"""YouTube transcript fetching. Free, no API-quota cost."""
from __future__ import annotations

from typing import List, Optional, TypedDict


class TranscriptSegment(TypedDict):
    text: str
    start: float
    duration: float


def fetch_transcript(video_id: str, language_allowlist: Optional[List[str]] = None) -> Optional[List[TranscriptSegment]]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    except ImportError:
        return None

    try:
        if language_allowlist:
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=language_allowlist)
        else:
            data = YouTubeTranscriptApi.get_transcript(video_id)
    except (NoTranscriptFound, TranscriptsDisabled, Exception):
        return None

    return [{"text": d["text"], "start": float(d["start"]), "duration": float(d["duration"])} for d in data]


def excerpt_for_window(segments: List[TranscriptSegment], start: float, end: float) -> str:
    parts = [s["text"] for s in segments if s["start"] >= start and s["start"] < end]
    return " ".join(parts).strip()
