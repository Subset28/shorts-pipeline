"""Orchestrates: URL -> platform detection -> discovery -> windowing ->
list[Candidate]. Shared by the CLI and the HTTP API so both stay in sync."""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from .config import load_config
from .models import Candidate
from .platforms import twitch as tw
from .platforms import youtube as yt
from .safety import build_safety_notes, rights_notes_for_platform
from .scout.clips import clip_to_candidate
from .scout.windowing import (
    distributed_fixed_interval_windows,
    fixed_interval_windows,
    score_transcript_windows,
)
from .transcript import excerpt_for_window, fetch_transcript
from .url_parse import parse_source


class ScoutError(RuntimeError):
    pass


def _days_since(iso_ts: Optional[str]) -> Optional[float]:
    if not iso_ts:
        return None
    try:
        published = datetime.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - published).total_seconds() / 86400
    except ValueError:
        return None


def _youtube_video_to_candidates(video: Dict[str, Any], cfg: Dict[str, Any], min_s: int, max_s: int) -> List[Candidate]:
    video_id = video["id"]
    snippet = video["snippet"]
    title = snippet.get("title", "")
    duration = yt.parse_iso8601_duration(video["contentDetails"]["duration"])
    view_count = int(video.get("statistics", {}).get("viewCount", 0))
    published_at = snippet.get("publishedAt")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    thumb = snippet.get("thumbnails", {}).get("high", {}).get("url")
    rights = rights_notes_for_platform("youtube")

    segments = fetch_transcript(video_id, cfg.get("language_allowlist"))

    if segments:
        windows = score_transcript_windows(
            segments,
            min_seconds=min_s,
            max_seconds=max_s,
            title=title,
            keyword_weights=cfg["scoring_weights"],
            excluded_terms=cfg.get("excluded_terms"),
            duration_hint=duration,
            view_count=view_count,
            published_recency_days=_days_since(published_at),
            max_windows=cfg["max_candidates_per_source"],
            min_gap_seconds=cfg["min_gap_between_selected_windows"],
        )
        low_confidence = False
    else:
        windows = distributed_fixed_interval_windows(
            duration,
            chunk_seconds=cfg["vod_chunk_seconds"],
            max_windows=cfg["max_candidates_per_source"],
        )
        low_confidence = True

    candidates = []
    for w in windows:
        excerpt = w.transcript_excerpt or (excerpt_for_window(segments, w.start_seconds, w.end_seconds) if segments else None)
        why = w.why_selected + (" [low confidence: no transcript, fixed-interval fallback]" if low_confidence else "")
        candidates.append(Candidate(
            source_id=f"yt:{video_id}:{int(w.start_seconds)}-{int(w.end_seconds)}",
            platform="youtube",
            candidate_kind="youtube_window",
            creator_name=snippet.get("channelTitle", ""),
            video_url=video_url,
            start_seconds=w.start_seconds,
            end_seconds=w.end_seconds,
            duration_seconds=w.end_seconds - w.start_seconds,
            title=title,
            why_selected=why,
            transcript_excerpt=excerpt,
            thumbnail_url=thumb,
            view_count=view_count,
            published_at=published_at,
            score=w.score,
            safety_notes=build_safety_notes(
                age_restricted=snippet.get("contentRating", {}).get("ytRating") == "ytAgeRestricted",
                title=title,
                transcript_excerpt=excerpt,
                flagged_keywords=cfg["safety"]["flagged_keywords"],
            ),
            **rights,
        ))
    return candidates


def _twitch_vod_to_candidates(vod: Dict[str, Any], cfg: Dict[str, Any], min_s: int, max_s: int) -> List[Candidate]:
    duration = tw.parse_duration_to_seconds(vod.get("duration", "0s"))
    windows = fixed_interval_windows(duration, chunk_seconds=cfg["vod_chunk_seconds"], max_windows=cfg["max_candidates_per_source"])
    title = vod.get("title", "")
    rights = rights_notes_for_platform("twitch_vod")

    candidates = []
    for w in windows:
        candidates.append(Candidate(
            source_id=f"twitch_vod:{vod['id']}:{int(w.start_seconds)}-{int(w.end_seconds)}",
            platform="twitch_vod",
            candidate_kind="twitch_vod_window",
            creator_name=vod.get("user_name", ""),
            video_url=vod.get("url", ""),
            start_seconds=w.start_seconds,
            end_seconds=w.end_seconds,
            duration_seconds=w.end_seconds - w.start_seconds,
            title=title,
            why_selected=w.why_selected,
            thumbnail_url=vod.get("thumbnail_url"),
            view_count=vod.get("view_count"),
            published_at=vod.get("published_at") or vod.get("created_at"),
            score=w.score,
            safety_notes=build_safety_notes(
                age_restricted=None,
                title=title,
                transcript_excerpt=None,
                flagged_keywords=cfg["safety"]["flagged_keywords"],
            ),
            **rights,
        ))
    return candidates


def scout(source_url: str, *, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None) -> List[Candidate]:
    cfg = load_config()
    min_s = min_seconds or cfg["min_clip_seconds"]
    max_s = max_seconds or cfg["max_clip_seconds"]

    parsed = parse_source(source_url)
    if not parsed:
        raise ScoutError(f"could not recognize platform/kind for URL: {source_url}")

    candidates: List[Candidate] = []

    if parsed.platform == "youtube":
        if not cfg["platforms_enabled"]["youtube"]:
            raise ScoutError("youtube platform disabled in config")

        if parsed.kind == "video":
            video = yt.get_video(parsed.identifier, daily_cap=cfg["youtube_daily_quota_cap"])
            if not video:
                raise ScoutError(f"YouTube video not found: {parsed.identifier}")
            candidates.extend(_youtube_video_to_candidates(video, cfg, min_s, max_s))
        elif parsed.kind == "channel":
            items = yt.get_recent_uploads(parsed.identifier, limit=cfg["youtube_search_limit"], daily_cap=cfg["youtube_daily_quota_cap"])
            for item in items:
                vid = item["contentDetails"]["videoId"]
                video = yt.get_video(vid, daily_cap=cfg["youtube_daily_quota_cap"])
                if video:
                    candidates.extend(_youtube_video_to_candidates(video, cfg, min_s, max_s))

    elif parsed.platform == "twitch":
        if not cfg["platforms_enabled"]["twitch"]:
            raise ScoutError("twitch platform disabled in config")

        if parsed.kind == "clip":
            clip = tw.get_clip_by_id(parsed.identifier)
            if not clip:
                raise ScoutError(f"Twitch clip not found: {parsed.identifier}")
            candidates.append(clip_to_candidate(clip, flagged_keywords=cfg["safety"]["flagged_keywords"]))
        elif parsed.kind == "vod":
            vod = tw.get_video_by_id(parsed.identifier)
            if not vod:
                raise ScoutError(f"Twitch VOD not found: {parsed.identifier}")
            candidates.extend(_twitch_vod_to_candidates(vod, cfg, min_s, max_s))
        elif parsed.kind == "channel":
            user = tw.get_user_by_login(parsed.identifier)
            if not user:
                raise ScoutError(f"Twitch channel not found: {parsed.identifier}")
            clips = tw.get_clips_for_broadcaster(user["id"], limit=cfg["max_candidates_per_source"])
            for clip in clips:
                candidates.append(clip_to_candidate(clip, flagged_keywords=cfg["safety"]["flagged_keywords"]))

    return candidates[: cfg["max_candidates_per_source"]]
