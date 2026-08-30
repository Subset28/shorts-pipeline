"""Loads config.json (tunables) + .env (secrets). Secrets never flow
through the config dict returned to the API."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

load_dotenv(ROOT / ".env")

REQUIRED_NUMERIC_RANGES = {
    "min_clip_seconds": (1, 3600),
    "max_clip_seconds": (1, 3600),
    "max_candidates_per_source": (1, 500),
    "twitch_clip_window_days": (1, 365),
    "youtube_search_limit": (1, 50),
    "vod_chunk_seconds": (5, 3600),
    "min_gap_between_selected_windows": (0, 3600),
    "youtube_daily_quota_cap": (100, 10000),
}


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def validate_config(cfg: Dict[str, Any]) -> None:
    """Raises ValueError on the first problem found."""
    for key, (lo, hi) in REQUIRED_NUMERIC_RANGES.items():
        if key not in cfg:
            continue
        val = cfg[key]
        if not isinstance(val, (int, float)) or not (lo <= val <= hi):
            raise ValueError(f"{key} must be a number between {lo} and {hi}, got {val!r}")

    if cfg.get("min_clip_seconds", 0) >= cfg.get("max_clip_seconds", 1):
        raise ValueError("min_clip_seconds must be < max_clip_seconds")


def merge_config(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow-merge one level deep for nested dict fields (scoring_weights, safety, platforms_enabled)."""
    merged = dict(base)
    for k, v in patch.items():
        if k not in base:
            raise ValueError(f"unknown config key: {k!r}")
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            nested = dict(base[k])
            for nk, nv in v.items():
                if nk not in nested:
                    raise ValueError(f"unknown config key: {k}.{nk!r}")
                nested[nk] = nv
            merged[k] = nested
        else:
            merged[k] = v
    return merged


def secrets_status() -> Dict[str, bool]:
    return {
        "twitch_configured": bool(os.getenv("TWITCH_CLIENT_ID") and os.getenv("TWITCH_CLIENT_SECRET")),
        "youtube_configured": bool(os.getenv("YOUTUBE_API_KEY")),
    }


def get_secret(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"missing required secret: {name} (set it in .env)")
    return val
