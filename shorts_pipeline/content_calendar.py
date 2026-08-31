from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from .models import Topic

_LONGFORM_CATEGORY_PRIORITY = {
    "AI": 7,
    "AI News": 7,
    "AI/ML": 7,
    "ML": 6,
    "Cyber": 6,
    "CS": 5,
    "Aerospace": 4,
    "Finance": 2,
}


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


def _longform_sort_key(topic: Topic) -> tuple[int, float]:
    return (_LONGFORM_CATEGORY_PRIORITY.get(topic.category, 1), topic.score)


def _experiment_targets(experiment_brief: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    targets: dict[str, list[dict[str, Any]]] = {}
    if not experiment_brief or experiment_brief.get("status") != "ready":
        return targets
    experiments = experiment_brief.get("experiments", [])
    if not isinstance(experiments, list):
        return targets
    for experiment in experiments:
        if not isinstance(experiment, dict):
            continue
        for role in ("reference", "baseline"):
            target = experiment.get(role)
            if isinstance(target, dict) and str(target.get("category", "")).strip():
                targets.setdefault(str(target["category"]), []).append(
                    {
                        "role": role,
                        "area": experiment.get("area", ""),
                        "metric": experiment.get("metric", ""),
                        "change": experiment.get("change", ""),
                        **target,
                    }
                )
    return targets


def _select_short_topics(topics: list[Topic], count: int, preferred_categories: list[str] | None = None) -> list[Topic]:
    by_category: dict[str, list[Topic]] = {}
    for topic in sorted(topics, key=lambda item: item.score, reverse=True):
        by_category.setdefault(topic.category or "Technology", []).append(topic)
    selected: list[Topic] = []
    preferred = [category for category in preferred_categories or [] if category in by_category]
    categories = preferred + [category for category in by_category if category not in preferred]
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
    experiment_brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a source-backed slate using explicitly renderable long-form topics."""
    if not 1 <= shorts_count <= 7:
        raise ValueError("shorts_count must be between 1 and 7")
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    unique = _unique_topics(topics)
    eligible_longform = _unique_topics(longform_topics or [])
    reserved_longform = (
        max(eligible_longform, key=_longform_sort_key) if include_longform and eligible_longform else None
    )
    short_pool = [
        topic for topic in unique if not reserved_longform or topic.sources[0].url != reserved_longform.sources[0].url
    ]
    targets = _experiment_targets(experiment_brief)
    selected = _select_short_topics(short_pool, shorts_count, list(targets))
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
                **(
                    {"analytics_target": targets[topic.category][0]}
                    if len(targets.get(topic.category, [])) == 1
                    else {}
                ),
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
