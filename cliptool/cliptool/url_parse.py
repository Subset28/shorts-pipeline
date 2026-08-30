"""Detects platform + resource kind + id from a pasted URL."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedSource:
    platform: str  # "youtube" | "twitch"
    kind: str      # "channel" | "video" | "vod" | "clip"
    identifier: str
    raw_url: str


_YT_VIDEO_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{6,})")
_YT_CHANNEL_RE = re.compile(r"youtube\.com/(?:channel/|c/|@)([\w-]+)")

_TWITCH_CLIP_RE = re.compile(r"twitch\.tv/(?:[\w]+/clip/|clips\.twitch\.tv/)([\w-]+)", re.I)
_TWITCH_VOD_RE = re.compile(r"twitch\.tv/videos/(\d+)", re.I)
_TWITCH_CHANNEL_RE = re.compile(r"twitch\.tv/([\w]+)/?$", re.I)


def parse_source(url: str) -> Optional[ParsedSource]:
    url = url.strip()

    m = _YT_VIDEO_RE.search(url)
    if m:
        return ParsedSource("youtube", "video", m.group(1), url)
    m = _YT_CHANNEL_RE.search(url)
    if m:
        return ParsedSource("youtube", "channel", m.group(1), url)

    m = _TWITCH_CLIP_RE.search(url)
    if m:
        return ParsedSource("twitch", "clip", m.group(1), url)
    m = _TWITCH_VOD_RE.search(url)
    if m:
        return ParsedSource("twitch", "vod", m.group(1), url)
    m = _TWITCH_CHANNEL_RE.search(url)
    if m:
        return ParsedSource("twitch", "channel", m.group(1), url)

    return None
