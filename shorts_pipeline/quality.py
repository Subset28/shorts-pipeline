from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

_SRT_TIMESTAMP = re.compile(
    r"\d+\n(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2},\d{3})"
)
_SRT_BLOCK = re.compile(
    r"(?ms)^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}\s*\n(.*?)(?=\n\s*\n|\Z)"
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


def probe_video_stream(path: Path | None) -> dict[str, float | int] | None:
    """Read video dimensions and frame rate when ffprobe can inspect the file."""
    if not path or not path.exists():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        stream = json.loads(result.stdout).get("streams", [None])[0]
        if not isinstance(stream, dict):
            return None
        width = int(stream["width"])
        height = int(stream["height"])
        frame_rate = float(Fraction(str(stream["r_frame_rate"])))
        return {"width": width, "height": height, "fps": frame_rate}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _timestamp_seconds(value: str) -> float:
    hours, minutes, remainder = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(remainder)


def caption_end(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    matches = _SRT_TIMESTAMP.findall(path.read_text(encoding="utf-8-sig"))
    return _timestamp_seconds(matches[-1][1]) if matches else None


def caption_start(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    matches = _SRT_TIMESTAMP.findall(path.read_text(encoding="utf-8-sig"))
    return _timestamp_seconds(matches[0][0]) if matches else None


def caption_word_count(path: Path | None) -> int | None:
    """Count caption words so truncated tracks cannot pass timing alone."""
    if not path or not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    words = []
    for block in _SRT_BLOCK.findall(text):
        cleaned = re.sub(r"<[^>]+>|\\{[^}]*\\}", " ", block)
        words.extend(re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", cleaned))
    return len(words)


def assess_render(
    video: Path, audio: Path | None, captions: Path | None, background: Path | None, background_looped: bool = False
) -> dict:
    """Return deterministic quality evidence for a rendered short."""
    video_duration = probe_duration(video)
    video_stream = probe_video_stream(video)
    audio_duration = probe_duration(audio)
    background_duration = probe_duration(background)
    first_caption = caption_start(captions)
    last_caption = caption_end(captions)
    caption_words = caption_word_count(captions)
    issues: list[str] = []
    if video_duration is None:
        issues.append("video_duration_unavailable")
    if video_stream:
        dimensions = (video_stream["width"], video_stream["height"])
        if dimensions not in {(720, 1280), (1080, 1920), (1280, 720), (1920, 1080)}:
            issues.append("video_resolution_unexpected")
        if float(video_stream["fps"]) < 24:
            issues.append("video_frame_rate_too_low")
    if audio_duration is None:
        issues.append("audio_duration_unavailable")
    av_delta = (
        abs(video_duration - audio_duration) if video_duration is not None and audio_duration is not None else None
    )
    if av_delta is not None and av_delta > 0.25:
        issues.append("audio_video_duration_mismatch")
    if (
        not background_looped
        and background_duration is not None
        and video_duration is not None
        and background_duration + 0.5 < video_duration
    ):
        issues.append("background_shorter_than_video")
    caption_coverage = (
        last_caption / audio_duration if last_caption is not None and audio_duration and audio_duration > 0 else None
    )
    if captions and caption_coverage is None:
        issues.append("caption_timing_unavailable")
    elif caption_coverage is not None:
        if first_caption is not None and first_caption > 1.0:
            issues.append("captions_start_too_late")
        if caption_coverage < 0.90:
            issues.append("captions_end_too_early")
        if caption_coverage > 1.05:
            issues.append("captions_end_too_late")
    if captions and caption_words is None:
        issues.append("caption_word_count_unavailable")
    elif caption_words is not None and audio_duration is not None and caption_words < max(5, audio_duration * 0.5):
        issues.append("captions_too_sparse")
    return {
        "passed": not issues,
        "video_duration_seconds": round(video_duration, 3) if video_duration is not None else None,
        "video_width": video_stream["width"] if video_stream else None,
        "video_height": video_stream["height"] if video_stream else None,
        "video_fps": round(float(video_stream["fps"]), 3) if video_stream else None,
        "audio_duration_seconds": round(audio_duration, 3) if audio_duration is not None else None,
        "background_duration_seconds": round(background_duration, 3) if background_duration is not None else None,
        "caption_start_seconds": round(first_caption, 3) if first_caption is not None else None,
        "caption_end_seconds": round(last_caption, 3) if last_caption is not None else None,
        "caption_word_count": caption_words,
        "caption_coverage": round(caption_coverage, 3) if caption_coverage is not None else None,
        "audio_video_delta_seconds": round(av_delta, 3) if av_delta is not None else None,
        "issues": issues,
    }
