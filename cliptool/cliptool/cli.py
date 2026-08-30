"""cliptool CLI: scout <url> -> candidates.json; fetch <id> -> clip.mp4."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .config import load_config
from .extractor import ExtractionError, download_segment, grab_preview_frames
from .models import Candidate
from .scout_engine import ScoutError, scout as run_scout


@click.group()
def cli():
    """cliptool — bounded-clip scout & extractor for Twitch/YouTube."""


@cli.command()
@click.option("--source", required=True, help="Channel/video/VOD/clip URL")
@click.option("--min", "min_seconds", type=int, default=None, help="Min clip seconds (default from config)")
@click.option("--max", "max_seconds", type=int, default=None, help="Max clip seconds (default from config)")
@click.option("--out", default="candidates.json", help="Output JSON path")
def scout(source: str, min_seconds: int, max_seconds: int, out: str):
    """Scout a source URL for bounded candidate segments."""
    try:
        candidates = run_scout(source, min_seconds=min_seconds, max_seconds=max_seconds)
    except ScoutError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(1)

    out_path = Path(out)
    out_path.write_text(
        json.dumps([c.model_dump() for c in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(f"wrote {len(candidates)} candidates -> {out_path}")


@cli.command()
@click.option("--candidates-file", default="candidates.json", help="Path to candidates.json")
@click.option("--candidate", "candidate_id", required=True, help="source_id of the candidate to fetch")
@click.option("--out", default=None, help="Output video path (default: outputs/<source_id>.mp4)")
@click.option("--frames/--no-frames", default=True, help="Also grab preview frames")
def fetch(candidates_file: str, candidate_id: str, out: str, frames: bool):
    """Download the exact bounded segment for one candidate."""
    data = json.loads(Path(candidates_file).read_text(encoding="utf-8"))
    match = next((c for c in data if c["source_id"] == candidate_id), None)
    if not match:
        click.echo(f"error: candidate {candidate_id!r} not found in {candidates_file}", err=True)
        sys.exit(1)

    candidate = Candidate(**match)
    safe_name = candidate_id.replace(":", "_").replace("/", "_")
    out_path = Path(out) if out else Path("outputs") / f"{safe_name}.mp4"

    try:
        download_segment(candidate, out_path)
        candidate.acquisition_status = "acquired"
    except ExtractionError as e:
        candidate.acquisition_status = "blocked"
        candidate.acquisition_detail = str(e)
        click.echo(f"error: {e}", err=True)
        _update_candidate_in_file(candidates_file, candidate)
        sys.exit(1)

    if frames:
        mid = (candidate.start_seconds + candidate.end_seconds) / 2
        span = candidate.end_seconds - candidate.start_seconds
        at = [0.1 * span, mid - candidate.start_seconds, 0.9 * span]
        candidate.preview_frames = grab_preview_frames(out_path, at_seconds=at, out_dir=out_path.parent)

    _update_candidate_in_file(candidates_file, candidate)
    click.echo(f"fetched -> {out_path}")


def _update_candidate_in_file(candidates_file: str, candidate: Candidate) -> None:
    path = Path(candidates_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    for i, c in enumerate(data):
        if c["source_id"] == candidate.source_id:
            data[i] = candidate.model_dump()
            break
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8787, type=int)
def serve(host: str, port: int):
    """Run the local config/scout/fetch HTTP API."""
    import uvicorn
    uvicorn.run("api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    cli()
