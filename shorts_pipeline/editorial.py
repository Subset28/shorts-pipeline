from __future__ import annotations

from datetime import date
from typing import Any

from .models import Topic
from .seo import eligible_formats, fallback_package

REDDIT_URL_PREFIXES = ("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/")

_VISUAL_DIRECTIONS = {
    "AI": "Use intentional AI/ML development footage, then add a simple diagram or product UI that explains the claim.",
    "AI News": "Use intentional AI development or robotics footage, with a diagram that makes the announcement concrete.",
    "ML": "Use model-training or code visuals, with one legible chart or pipeline step tied to the source.",
    "CS": "Use code, terminal, or systems footage, with a diagram of the failure or engineering tradeoff.",
    "Cyber": "Use defensive security visuals only, with a simple attack-surface or mitigation diagram; do not show exploit steps.",
    "Aerospace": "Use mission or spacecraft footage, with a clean timeline showing the milestone and the next test.",
}


def _source_type(topic: Topic) -> str:
    source = topic.sources[0]
    return (
        "reddit_anecdote"
        if source.community and source.url.lower().startswith(REDDIT_URL_PREFIXES)
        else "reported_source"
    )


def build_editorial_brief(topic: Topic, analytics_target: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turn one source-backed topic into a reviewable production brief."""
    if not topic.sources:
        raise ValueError("editorial brief requires a source")
    source = topic.sources[0]
    is_reddit = _source_type(topic) == "reddit_anecdote"
    if is_reddit and not source.reuse_permission:
        raise ValueError("editorial brief requires explicit Reddit reuse permission")
    package = fallback_package(topic)
    formats = eligible_formats(topic)
    return {
        "source": {
            "title": source.title,
            "url": source.url,
            "published": source.published,
            "author": source.author,
            "community": source.community,
            "type": _source_type(topic),
        },
        "evidence": {
            "claim": source.summary,
            "verification": "Recheck the source immediately before narration and preserve the source URL in metadata.",
        },
        "creative": {
            "category": topic.category,
            "format_name": package.format_name,
            "eligible_formats": list(formats),
            "hook": package.hook,
            "visual_direction": _VISUAL_DIRECTIONS.get(
                topic.category, "Use footage that directly illustrates the source claim."
            ),
            "caption_plan": "One readable idea per caption burst; emphasize the hook, concrete result, and final takeaway.",
        },
        "metadata": {
            "title": package.title,
            "description": package.description,
            "tags": list(package.tags),
        },
        "longform_bridge": {
            "question": f"What does this source reveal about {topic.category.lower()} beyond the headline?",
            "chapters": [
                "What happened",
                "How it works",
                "What the source proves",
                "What remains uncertain",
                "Takeaway",
            ],
        },
        "rights": {
            "reuse_permission": source.reuse_permission,
            "attribution_required": is_reddit,
            "background_rule": "Use only cataloged footage with recorded provenance; original generated visuals are preferred when available.",
        },
        "analytics_target": analytics_target,
        "privacy_status": "private",
    }


def _unique_topics(topics: list[Topic]) -> list[Topic]:
    by_url: dict[str, Topic] = {}
    for topic in topics:
        if not topic.sources:
            continue
        url = topic.sources[0].url
        if url and (url not in by_url or topic.score > by_url[url].score):
            by_url[url] = topic
    return sorted(by_url.values(), key=lambda item: item.score, reverse=True)


def build_research_week(
    topics: list[Topic], week_start: date, shorts_count: int = 7, include_longform: bool = True
) -> dict[str, Any]:
    """Create a private, source-backed editorial slate without rendering or publishing."""
    if not 1 <= shorts_count <= 7:
        raise ValueError("shorts_count must be between 1 and 7")
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    unique = _unique_topics(topics)
    required_topics = shorts_count + (1 if include_longform else 0)
    if len(unique) < required_topics:
        raise ValueError(f"research slate needs at least {required_topics} unique topics")
    longform_topic = unique[0] if include_longform and unique else None
    short_topics = [
        topic for topic in unique if not longform_topic or topic.sources[0].url != longform_topic.sources[0].url
    ]
    short_topics = short_topics[:shorts_count]
    shorts = [build_editorial_brief(topic) for topic in short_topics]
    longform = [build_editorial_brief(longform_topic)] if longform_topic else []
    return {
        "week_of": week_start.isoformat(),
        "privacy_status": "private",
        "shorts": shorts,
        "longform": longform,
    }
