"""Twitch clips are already bounded by the creator — no windowing
needed, just map Helix clip metadata straight onto our Candidate schema."""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import Candidate
from ..safety import build_safety_notes, rights_notes_for_platform


def clip_to_candidate(clip: Dict[str, Any], *, flagged_keywords: List[str]) -> Candidate:
    duration = float(clip.get("duration", 0))
    title = clip.get("title", "")
    rights = rights_notes_for_platform("twitch_clip")

    return Candidate(
        source_id=f"twitch_clip:{clip['id']}",
        platform="twitch_clip",
        candidate_kind="twitch_clip",
        creator_name=clip.get("broadcaster_name", ""),
        video_url=clip.get("url", ""),
        start_seconds=0,
        end_seconds=duration,
        duration_seconds=duration,
        title=title,
        why_selected="pre-bounded Twitch clip (creator-selected highlight)",
        thumbnail_url=clip.get("thumbnail_url"),
        clip_view_count=clip.get("view_count"),
        game_or_topic=clip.get("game_id"),
        published_at=clip.get("created_at"),
        safety_notes=build_safety_notes(
            age_restricted=None,
            title=title,
            transcript_excerpt=None,
            flagged_keywords=flagged_keywords,
        ),
        score=min((clip.get("view_count") or 0) / 10000, 1.0),
        **rights,
    )
