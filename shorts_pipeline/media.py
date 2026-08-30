from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def download_rights_cleared_source(url: str, output_dir: Path) -> Path:
    """Download a user-authorized source with yt-dlp.

    This adapter deliberately requires an explicit URL and is not used for
    discovery. Callers must maintain rights/provenance for downloaded media.
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp is required for source-media downloads")
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "source.%(ext)s")
    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "--format", "bv*+ba/b", "--merge-output-format", "mp4", "--output", template, url],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    candidates = sorted(output_dir.glob("source.*"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError(f"yt-dlp completed without producing media: {result.stderr[-300:]}")
    return candidates[0]
