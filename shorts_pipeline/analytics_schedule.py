from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CHECKPOINT = timedelta(hours=24)


def _timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_publications(events_path: Path) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    if not events_path.exists():
        return []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        video_id = str(event.get("platform_id", "")).strip()
        uploaded_at = _timestamp(event.get("timestamp", ""))
        if event.get("event") != "youtube_published" or not video_id or not uploaded_at:
            continue
        found.setdefault(
            video_id,
            {
                "video_id": video_id,
                "uploaded_at": uploaded_at.isoformat(),
                "source_url": event.get("source_url", ""),
                "category": event.get("category", "unknown"),
                "format_name": event.get("format_name", "unknown"),
            },
        )
    return sorted(found.values(), key=lambda item: item["uploaded_at"])


def _snapshots(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def due_videos(events_path: Path, snapshots_path: Path, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    snapshots = _snapshots(snapshots_path)
    due = []
    for publication in load_publications(events_path):
        uploaded_at = _timestamp(publication["uploaded_at"])
        if not uploaded_at or now - uploaded_at < CHECKPOINT:
            continue
        prior = [
            _timestamp(item.get("collected_at", ""))
            for item in snapshots.get(publication["video_id"], [])
            if isinstance(item, dict)
        ]
        prior = [item for item in prior if item]
        if not prior or now - max(prior) >= CHECKPOINT:
            due.append(publication)
    return due


def week_videos(events_path: Path, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return [item for item in load_publications(events_path) if start <= _timestamp(item["uploaded_at"]) < end]
