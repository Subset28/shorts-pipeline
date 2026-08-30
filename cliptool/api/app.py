"""Local-only HTTP API: config read/write for agents, plus scout/fetch
endpoints so the same logic is drivable over HTTP or CLI.

Binds 127.0.0.1 by default (see cliptool.cli `serve`). No auth — nothing
sensitive is ever exposed: secrets stay in .env and are only reported as
booleans (`"twitch_configured"`), never as values, and no endpoint here
accepts a secret value.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cliptool.config import load_config, merge_config, save_config, secrets_status, validate_config
from cliptool.extractor import ExtractionError, download_segment, grab_preview_frames
from cliptool.models import Candidate
from cliptool.scout_engine import ScoutError, scout as run_scout

app = FastAPI(title="cliptool API", version="1.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "secrets": secrets_status()}


@app.get("/config")
def get_config() -> Dict[str, Any]:
    cfg = load_config()
    cfg["_secrets_status"] = secrets_status()
    return cfg


class ConfigPatch(BaseModel):
    patch: Dict[str, Any]


@app.put("/config")
def update_config(body: ConfigPatch) -> Dict[str, Any]:
    cfg = load_config()
    try:
        merged = merge_config(cfg, body.patch)
        validate_config(merged)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    save_config(merged)
    return merged


@app.get("/config/schema")
def config_schema() -> Dict[str, Any]:
    return {
        "min_clip_seconds": "int, seconds, must be < max_clip_seconds",
        "max_clip_seconds": "int, seconds",
        "max_candidates_per_source": "int, cap on candidates returned per scout call",
        "twitch_clip_window_days": "int, how many days back to look for clips",
        "youtube_search_limit": "int, max uploads to scan per channel scout",
        "vod_chunk_seconds": "int, fixed-interval fallback chunk size",
        "min_gap_between_selected_windows": "int, seconds of separation enforced between selected windows",
        "language_allowlist": "list[str], transcript language codes to prefer",
        "excluded_terms": "list[str], windows containing these terms are skipped",
        "include_shorts": "bool",
        "youtube_daily_quota_cap": "int, hard stop for YouTube Data API v3 units/day (free tier = 10000)",
        "scoring_weights": "dict[str,float]: keyword_density, title_keyword_match, punctuation_excitement, transcript_density_spike, short_duration_preference, recency, popularity",
        "safety": "dict: flag_age_restricted (bool), flagged_keywords (list[str])",
        "platforms_enabled": "dict: youtube (bool), twitch (bool)",
        "_secrets": "not editable here — set TWITCH_CLIENT_ID/SECRET and YOUTUBE_API_KEY in .env",
    }


class ScoutRequest(BaseModel):
    source: str
    min: Optional[int] = None
    max: Optional[int] = None
    out: str = "candidates.json"


@app.post("/scout")
def scout_endpoint(req: ScoutRequest) -> Dict[str, Any]:
    try:
        candidates = run_scout(req.source, min_seconds=req.min, max_seconds=req.max)
    except ScoutError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dumped = [c.model_dump() for c in candidates]
    Path(req.out).write_text(json.dumps(dumped, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"count": len(dumped), "out": req.out, "candidates": dumped}


class FetchRequest(BaseModel):
    candidates_file: str = "candidates.json"
    candidate_id: str
    out: Optional[str] = None
    frames: bool = True


@app.post("/fetch")
def fetch_endpoint(req: FetchRequest) -> Dict[str, Any]:
    path = Path(req.candidates_file)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{req.candidates_file} not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    match = next((c for c in data if c["source_id"] == req.candidate_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"candidate {req.candidate_id!r} not found")

    candidate = Candidate(**match)
    safe_name = req.candidate_id.replace(":", "_").replace("/", "_")
    out_path = Path(req.out) if req.out else Path("outputs") / f"{safe_name}.mp4"

    try:
        download_segment(candidate, out_path)
        candidate.acquisition_status = "acquired"
    except ExtractionError as e:
        candidate.acquisition_status = "blocked"
        candidate.acquisition_detail = str(e)
        _write_back(path, data, candidate)
        raise HTTPException(status_code=422, detail=str(e))

    if req.frames:
        mid = (candidate.start_seconds + candidate.end_seconds) / 2
        span = candidate.end_seconds - candidate.start_seconds
        at = [0.1 * span, mid - candidate.start_seconds, 0.9 * span]
        candidate.preview_frames = grab_preview_frames(out_path, at_seconds=at, out_dir=out_path.parent)

    _write_back(path, data, candidate)
    return {"out": str(out_path), "candidate": candidate.model_dump()}


def _write_back(path: Path, data: List[Dict[str, Any]], candidate: Candidate) -> None:
    for i, c in enumerate(data):
        if c["source_id"] == candidate.source_id:
            data[i] = candidate.model_dump()
            break
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
