from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SRT_TIMESTAMP = re.compile(
    r"\d+\n\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2},\d{3})"
)


def probe_duration(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return max(0.0, float(result.stdout.strip()))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _timestamp_seconds(value: str) -> float:
    hours, minutes, remainder = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(remainder)


def caption_end(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    matches = _SRT_TIMESTAMP.findall(path.read_text(encoding="utf-8-sig"))
    return _timestamp_seconds(matches[-1]) if matches else None


def assess_render(video: Path, audio: Path | None, captions: Path | None, background: Path | None) -> dict:
    """Return deterministic quality evidence for a rendered short."""
    video_duration = probe_duration(video)
    audio_duration = probe_duration(audio)
    background_duration = probe_duration(background)
    last_caption = caption_end(captions)
    issues: list[str] = []
    if video_duration is None:
        issues.append("video_duration_unavailable")
    if audio_duration is None:
        issues.append("audio_duration_unavailable")
    av_delta = (
        abs(video_duration - audio_duration) if video_duration is not None and audio_duration is not None else None
    )
    if av_delta is not None and av_delta > 0.25:
        issues.append("audio_video_duration_mismatch")
    if background_duration is not None and video_duration is not None and background_duration + 0.5 < video_duration:
        issues.append("background_shorter_than_video")
    caption_coverage = (
        last_caption / audio_duration if last_caption is not None and audio_duration and audio_duration > 0 else None
    )
    if captions and caption_coverage is None:
        issues.append("caption_timing_unavailable")
    elif caption_coverage is not None:
        if caption_coverage < 0.90:
            issues.append("captions_end_too_early")
        if caption_coverage > 1.05:
            issues.append("captions_end_too_late")
    return {
        "passed": not issues,
        "video_duration_seconds": round(video_duration, 3) if video_duration is not None else None,
        "audio_duration_seconds": round(audio_duration, 3) if audio_duration is not None else None,
        "background_duration_seconds": round(background_duration, 3) if background_duration is not None else None,
        "caption_end_seconds": round(last_caption, 3) if last_caption is not None else None,
        "caption_coverage": round(caption_coverage, 3) if caption_coverage is not None else None,
        "audio_video_delta_seconds": round(av_delta, 3) if av_delta is not None else None,
        "issues": issues,
    }
