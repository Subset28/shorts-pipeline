"""YouTube Data API v3 client. Quota-aware: every call goes through
quota.consume() first and raises QuotaExceeded rather than silently
burning past the free-tier daily cap."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .. import quota
from ..config import get_secret

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeError(RuntimeError):
    pass


def _api_key() -> str:
    return get_secret("YOUTUBE_API_KEY")


def get_video(video_id: str, *, daily_cap: int) -> Optional[Dict[str, Any]]:
    quota.consume("videos.list", daily_cap)
    resp = requests.get(f"{API_BASE}/videos", params={
        "part": "snippet,contentDetails,statistics",
        "id": video_id,
        "key": _api_key(),
    }, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0] if items else None


def get_channel_by_handle_or_id(identifier: str, *, daily_cap: int) -> Optional[Dict[str, Any]]:
    quota.consume("channels.list", daily_cap)
    params = {"part": "snippet,contentDetails", "key": _api_key()}
    if identifier.startswith("UC"):
        params["id"] = identifier
    else:
        params["forHandle"] = identifier if identifier.startswith("@") else f"@{identifier}"

    resp = requests.get(f"{API_BASE}/channels", params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0] if items else None


def get_recent_uploads(channel_id: str, *, limit: int, daily_cap: int) -> List[Dict[str, Any]]:
    channel = get_channel_by_handle_or_id(channel_id, daily_cap=daily_cap)
    if not channel:
        return []
    uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    quota.consume("playlistItems.list", daily_cap)
    resp = requests.get(f"{API_BASE}/playlistItems", params={
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": min(limit, 50),
        "key": _api_key(),
    }, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def parse_iso8601_duration(duration: str) -> float:
    """'PT1H2M3S' -> seconds."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0.0
    h, m, s = (int(g) if g else 0 for g in match.groups())
    return float(h * 3600 + m * 60 + s)
