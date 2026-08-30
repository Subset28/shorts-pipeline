"""Twitch Helix API client (app-only, Client Credentials flow).
Used for discovery only — actual downloads go through yt-dlp."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ..config import get_secret

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_BASE = "https://api.twitch.tv/helix"

_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0}


class TwitchError(RuntimeError):
    pass


def _get_app_token() -> str:
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    client_id = get_secret("TWITCH_CLIENT_ID")
    client_secret = get_secret("TWITCH_CLIENT_SECRET")

    resp = requests.post(TOKEN_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }, timeout=15)
    if resp.status_code != 200:
        raise TwitchError(f"failed to get Twitch app token: {resp.status_code} {resp.text[:300]}")

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return data["access_token"]


def _headers() -> Dict[str, str]:
    return {
        "Client-Id": get_secret("TWITCH_CLIENT_ID"),
        "Authorization": f"Bearer {_get_app_token()}",
    }


def get_user_by_login(login: str) -> Optional[Dict[str, Any]]:
    resp = requests.get(f"{HELIX_BASE}/users", headers=_headers(), params={"login": login}, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None


def get_clips_for_broadcaster(broadcaster_id: str, *, limit: int = 25, started_at: Optional[str] = None) -> List[Dict[str, Any]]:
    params = {"broadcaster_id": broadcaster_id, "first": min(limit, 100)}
    if started_at:
        params["started_at"] = started_at

    clips: List[Dict[str, Any]] = []
    cursor = None
    while len(clips) < limit:
        if cursor:
            params["after"] = cursor
        resp = requests.get(f"{HELIX_BASE}/clips", headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        clips.extend(body.get("data", []))
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor:
            break
    return clips[:limit]


def get_clip_by_id(clip_id: str) -> Optional[Dict[str, Any]]:
    resp = requests.get(f"{HELIX_BASE}/clips", headers=_headers(), params={"id": clip_id}, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None


def get_videos_for_user(user_id: str, *, limit: int = 10, video_type: str = "archive") -> List[Dict[str, Any]]:
    """video_type='archive' -> VODs."""
    params = {"user_id": user_id, "first": min(limit, 100), "type": video_type}
    resp = requests.get(f"{HELIX_BASE}/videos", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", [])[:limit]


def get_video_by_id(video_id: str) -> Optional[Dict[str, Any]]:
    resp = requests.get(f"{HELIX_BASE}/videos", headers=_headers(), params={"id": video_id}, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None


def parse_duration_to_seconds(duration_str: str) -> float:
    """Twitch VOD durations look like '1h2m3s'."""
    import re
    h = m = s = 0
    match = re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", duration_str)
    if match:
        h, m, s = (int(g) if g else 0 for g in match.groups())
    return h * 3600 + m * 60 + s
