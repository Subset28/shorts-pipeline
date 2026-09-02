"""Lawful, non-copying intelligence from public competitor metadata."""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

MIN_CHANNELS = 10
MAX_CHANNELS = 20
MIN_PATTERN_CHANNELS = 3
SENSITIVE_FIELD_TERMS = ("token", "cookie", "secret", "password", "authorization", "api_key", "credential")
ABSTRACT_FIELDS = (
    "hook_archetype",
    "first_visual",
    "context_seconds",
    "escalation_seconds",
    "mechanism_seconds",
    "payoff_seconds",
    "shot_count",
    "caption_words_per_burst",
    "ending_type",
)


class MetadataProvider(Protocol):
    def videos_for_channels(self, channel_ids: Sequence[str]) -> Sequence[Mapping[str, Any]]: ...


def _number(value: Any, *, integer: bool = False) -> int | float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0 if integer else 0.0
    if not math.isfinite(parsed) or parsed < 0:
        return 0 if integer else 0.0
    return int(parsed) if integer else parsed


def _timestamp(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("published_at must be an ISO timestamp") from None
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def compute_velocity(views: int | float, hours_since_publish: int | float) -> float:
    """Return views/hour with the contract's six-hour floor."""
    return _number(views) / max(_number(hours_since_publish), 6.0)


def channel_outlier(views: int | float, comparable_views: Sequence[int | float]) -> float:
    values = [_number(value) for value in comparable_views if _number(value) > 0]
    if not values:
        return 0.0
    return _number(views) / statistics.median(values)


def _validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    for key in record:
        if any(term in str(key).lower() for term in SENSITIVE_FIELD_TERMS):
            raise ValueError(f"sensitive field is not permitted: {key}")
    channel_id = str(record.get("channel_id", "")).strip()
    video_id = str(record.get("video_id", "")).strip()
    if not channel_id or not video_id:
        raise ValueError("metadata requires channel_id and video_id")
    published = _timestamp(record.get("published_at"))
    result: dict[str, Any] = {
        "channel_id": channel_id,
        "video_id": video_id,
        "published_at": published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "views": _number(record.get("views"), integer=True),
        "likes": _number(record.get("likes"), integer=True),
        "comments": _number(record.get("comments"), integer=True),
        "duration_seconds": _number(record.get("duration_seconds"), integer=True),
    }
    for field in ABSTRACT_FIELDS:
        value = record.get(field, "")
        result[field] = _number(value) if field.endswith("seconds") else _number(value, integer=True) if field in {"shot_count", "caption_words_per_burst"} else str(value).strip()
    return result


def load_metadata_fixture(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("metadata fixture is unreadable") from exc
    records = payload.get("videos") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("metadata fixture must contain a videos list")
    return [_validate_record(item) for item in records if isinstance(item, Mapping)]


def collect_metadata(provider: MetadataProvider, channel_ids: Sequence[str]) -> list[dict[str, Any]]:
    ids = tuple(sorted({str(item).strip() for item in channel_ids if str(item).strip()}))
    if not MIN_CHANNELS <= len(ids) <= MAX_CHANNELS:
        raise ValueError("competitor cohort must contain 10 to 20 channels")
    return [_validate_record(item) for item in provider.videos_for_channels(ids) if isinstance(item, Mapping)]


def _age_hours(record: Mapping[str, Any], now: datetime) -> float:
    return max(0.0, (now - _timestamp(record["published_at"])).total_seconds() / 3600)


def _metrics(records: Sequence[Mapping[str, Any]], now: datetime) -> list[dict[str, Any]]:
    by_channel: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_channel.setdefault(str(record["channel_id"]), []).append(record)
    output = []
    for record in records:
        age = _age_hours(record, now)
        peers = sorted(
            (peer for peer in by_channel[record["channel_id"]] if peer["video_id"] != record["video_id"]),
            key=lambda peer: abs(_age_hours(peer, now) - age),
        )[:10]
        views = int(record["views"])
        output.append(
            {
                **dict(record),
                "velocity": round(compute_velocity(views, age), 4),
                "channel_outlier": round(channel_outlier(views, [peer["views"] for peer in peers]), 4),
                "engagement_rate": round((record["likes"] + record["comments"]) / max(views, 1), 6),
            }
        )
    return output


def build_research_packet(records: Sequence[Mapping[str, Any]], generated_at: datetime) -> dict[str, Any]:
    normalized = [_validate_record(item) for item in records]
    channels = sorted({item["channel_id"] for item in normalized})
    if not MIN_CHANNELS <= len(channels) <= MAX_CHANNELS:
        raise ValueError("competitor cohort must contain 10 to 20 channels")
    now = generated_at if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc)
    scored = _metrics(normalized, now)
    patterns = []
    for hook in sorted({item["hook_archetype"] for item in scored if item["hook_archetype"]}):
        matches = [item for item in scored if item["hook_archetype"] == hook]
        independent = sorted({item["channel_id"] for item in matches})
        if len(independent) < MIN_PATTERN_CHANNELS:
            continue
        patterns.append({
            "hook_archetype": hook,
            "independent_channels": len(independent),
            "sample_size": len(matches),
            "mean_outlier": round(statistics.mean(item["channel_outlier"] for item in matches), 4),
            "mean_velocity": round(statistics.mean(item["velocity"] for item in matches), 4),
            "evidence": "repeated across independent channel outliers",
        })
    outliers = sorted(scored, key=lambda item: (-item["channel_outlier"], -item["velocity"], item["video_id"]))[:20]
    return {
        "spec_version": "competitor-research-v1",
        "generated_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cohort": {"channel_ids": channels, "channel_count": len(channels)},
        "outliers": outliers,
        "patterns": patterns,
        "production_media": [],
        "rights_note": "metadata and abstract features only; competitor media is not production media",
    }
