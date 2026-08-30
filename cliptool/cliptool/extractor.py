"""Downloads a candidate's exact bounded segment via yt-dlp, and grabs
preview frames via ffmpeg. Both are invoked as subprocesses so this
tool doesn't hard-depend on their Python bindings."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .models import Candidate


class ExtractionError(RuntimeError):
    pass


def _seconds_to_hhmmss(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def check_dependencies() -> List[str]:
    missing = []
    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    return missing


def download_segment(candidate: Candidate, out_path: Path) -> None:
    """Downloads only [start_seconds, end_seconds) of candidate.video_url."""
    missing = check_dependencies()
    if "yt-dlp" in missing:
        raise ExtractionError("yt-dlp not found on PATH; install it to fetch segments")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    section = f"*{_seconds_to_hhmmss(candidate.start_seconds)}-{_seconds_to_hhmmss(candidate.end_seconds)}"

    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "--force-keyframes-at-cuts",
        "-o", str(out_path),
        candidate.video_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExtractionError(f"yt-dlp failed: {result.stderr.strip()[-2000:]}")


def grab_preview_frames(video_path: Path, *, at_seconds: List[float], out_dir: Path) -> List[str]:
    if shutil.which("ffmpeg") is None:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: List[str] = []
    for i, t in enumerate(at_seconds):
        out_file = out_dir / f"{video_path.stem}_frame{i}.jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", str(max(0, t)),
            "-i", str(video_path),
            "-frames:v", "1",
            str(out_file),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and out_file.exists():
            frame_paths.append(str(out_file))
    return frame_paths
