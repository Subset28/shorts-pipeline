from datetime import date

import pytest

from shorts_pipeline.content_calendar import build_weekly_plan
from shorts_pipeline.models import Source, Topic


def _topic(title: str, category: str, score: float) -> Topic:
    source = Source(
        title,
        f"https://example.test/{title.replace(' ', '-')}",
        "A source-backed technical finding.",
        author="author",
        community="technology",
        reuse_permission=True,
    )
    return Topic(title, category, (source,), score)


def test_weekly_plan_balances_categories_and_reserves_longform_slot():
    topics = [
        _topic("AI systems", "AI", 10),
        _topic("Kernel incident", "CS", 9),
        _topic("Security failure", "Cyber", 8),
        _topic("Rocket test", "Aerospace", 7),
        _topic("ML benchmark", "ML", 6),
    ]

    plan = build_weekly_plan(
        topics,
        date(2026, 9, 7),
        shorts_count=4,
        include_longform=True,
        longform_topics=[topics[-1]],
    )

    assert len(plan) == 5
    assert [item["kind"] for item in plan] == ["short", "short", "short", "short", "longform"]
    assert {item["category"] for item in plan[:4]} == {"AI", "CS", "Cyber", "Aerospace"}
    assert plan[-1]["privacy_status"] == "private"
    assert plan[-1]["publish_at"].startswith("2026-09-13T")
    assert plan[-1]["source_url"] == "https://example.test/ML-benchmark"
    assert plan[-1]["author"] == "author"
    assert plan[-1]["subreddit"] == "technology"
    assert plan[-1]["reuse_permission"] is True
    assert all(item["source_url"].startswith("https://example.test/") for item in plan)


def test_weekly_plan_deduplicates_sources_and_limits_count():
    topic = _topic("One story", "CS", 4)
    duplicate = Topic(topic.title, topic.category, topic.sources, 99)

    plan = build_weekly_plan([topic, duplicate], date(2026, 9, 7), shorts_count=3, include_longform=False)

    assert len(plan) == 1
    assert plan[0]["publish_at"] == "2026-09-07T18:00:00+00:00"


def test_weekly_plan_omits_unrenderable_longform_sources():
    topic = _topic("RSS story", "AI/ML", 10)
    plan = build_weekly_plan([topic], date(2026, 9, 7), shorts_count=1, include_longform=True)
    assert [item["kind"] for item in plan] == ["short"]


def test_weekly_plan_omits_duplicate_longform_source():
    topic = _topic("Only story", "CS", 10)
    plan = build_weekly_plan([topic], date(2026, 9, 7), shorts_count=1, include_longform=True, longform_topics=[topic])
    assert [item["kind"] for item in plan] == ["longform"]


def test_weekly_plan_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="shorts_count"):
        build_weekly_plan([], date(2026, 9, 7), shorts_count=0)
    with pytest.raises(ValueError, match="between 1 and 7"):
        build_weekly_plan([], date(2026, 9, 7), shorts_count=8)
    with pytest.raises(ValueError, match="Monday"):
        build_weekly_plan([], date(2026, 9, 8))
