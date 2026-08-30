"""Tracks YouTube Data API v3 daily quota usage locally so we never
blow past the free tier (10,000 units/day)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent.parent
QUOTA_PATH = ROOT / "cache" / "youtube_quota.json"

# Approximate costs per YouTube Data API v3 endpoint (units).
COSTS = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
}


class QuotaExceeded(RuntimeError):
    pass


def _load() -> Dict:
    if not QUOTA_PATH.exists():
        return {"date": str(date.today()), "used": 0}
    with open(QUOTA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("date") != str(date.today()):
        return {"date": str(date.today()), "used": 0}
    return data


def _save(data: Dict) -> None:
    QUOTA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def used_today() -> int:
    return _load()["used"]


def consume(endpoint: str, daily_cap: int) -> None:
    """Raises QuotaExceeded without mutating state if consuming would
    exceed daily_cap; otherwise records the cost."""
    cost = COSTS.get(endpoint, 1)
    data = _load()
    if data["used"] + cost > daily_cap:
        raise QuotaExceeded(
            f"YouTube quota cap reached ({data['used']}/{daily_cap} units used today); "
            f"refusing {endpoint} (cost {cost})"
        )
    data["used"] += cost
    _save(data)
