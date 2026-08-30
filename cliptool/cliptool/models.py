"""Candidate schema shared by candidates.json and selected_for_render.json."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    source_id: str
    platform: str  # "youtube" | "twitch_clip" | "twitch_vod"
    candidate_kind: str  # "youtube_window" | "twitch_clip" | "twitch_vod_window"
    creator_name: str
    video_url: str
    original_source_url: Optional[str] = None

    start_seconds: float
    end_seconds: float
    duration_seconds: float

    title: str
    why_selected: str

    transcript_excerpt: Optional[str] = None
    preview_frames: List[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None

    view_count: Optional[int] = None
    clip_view_count: Optional[int] = None
    game_or_topic: Optional[str] = None

    license_or_rights_note: Optional[str] = None
    reuse_risk_note: Optional[str] = None
    safety_notes: List[str] = Field(default_factory=list)

    score: float = 0.0
    published_at: Optional[str] = None

    acquisition_status: str = "pending"  # pending | acquired | blocked | partial
    acquisition_detail: Optional[str] = None
