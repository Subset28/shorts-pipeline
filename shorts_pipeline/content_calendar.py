from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from .models import Topic


def _publish_at(day: date, hour: int) -> str:
    return datetime.combine(day, time(hour, tzinfo=timezone.utc)).isoformat()


def _unique_topics(topics: list[Topic]) -> list[Topic]:
    found: dict[str, Topic] = {}
    for topic in topics:
        if topic.sources and topic.sources[0].url:
            source_url = topic.sources[0].url
            if source_url not in found or topic.score > found[source_url].score:
                found[source_url] = topic
    return list(found.values())


def _select_short_topics(topics: list[Topic], count: int) -> list[Topic]:
    by_category: dict[str, list[Topic]] = {}
    for topic in sorted(topics, key=lambda item: item.score, reverse=True):
        by_category.setdefault(topic.category or "Technology", []).append(topic)
    selected: list[Topic] = []
    categories = list(by_category)
    while categories and len(selected) < count:
        next_categories: list[str] = []
        for category in categories:
            queue = by_category[category]
            if queue:
                selected.append(queue.pop(0))
            if queue:
                next_categories.append(category)
            if len(selected) == count:
                break
        categories = next_categories
    return selected


def build_weekly_plan(
    topics: list[Topic],
    week_start: date,
    shorts_count: int = 7,
    include_longform: bool = True,
    longform_topics: list[Topic] | None = None,
) -> list[dict[str, Any]]:
    """Build a source-backed slate using explicitly renderable long-form topics."""
    if not 1 <= shorts_count <= 7:
        raise ValueError("shorts_count must be between 1 and 7")
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    unique = _unique_topics(topics)
    eligible_longform = _unique_topics(longform_topics or [])
    reserved_longform = (
        max(eligible_longform, key=lambda item: item.score) if include_longform and eligible_longform else None
    )
    short_pool = [
        topic for topic in unique if not reserved_longform or topic.sources[0].url != reserved_longform.sources[0].url
    ]
    selected = _select_short_topics(short_pool, shorts_count)
    plan: list[dict[str, Any]] = []
    for index, topic in enumerate(selected):
        source = topic.sources[0]
        plan.append(
            {
                "kind": "short",
                "source_url": source.url,
                "source_title": source.title,
                "category": topic.category,
                "author": source.author,
                "subreddit": source.community,
                "reuse_permission": source.reuse_permission,
                "privacy_status": "private",
                "publish_at": _publish_at(week_start + timedelta(days=index), 18),
                "requires_review": True,
            }
        )
    if reserved_longform:
        topic = reserved_longform
        source = topic.sources[0]
        plan.append(
            {
                "kind": "longform",
                "source_url": source.url,
                "source_title": source.title,
                "category": topic.category,
                "author": source.author,
                "subreddit": source.community,
                "reuse_permission": source.reuse_permission,
                "privacy_status": "private",
                "publish_at": _publish_at(week_start + timedelta(days=6), 15),
                "requires_review": True,
            }
        )
    return plan
