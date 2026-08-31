from datetime import date

import pytest

from shorts_pipeline import cli
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


def test_weekly_production_rejects_public_plan(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text('{"privacy_status": "public", "entries": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="private"):
        cli.run_weekly_production(plan, tmp_path / "output")


def test_weekly_production_dispatches_render_only_entries(tmp_path, monkeypatch):
    source = Source(
        "Approved story",
        "https://reddit.test/story",
        "A complete story.",
        author="a",
        community="CS",
        reuse_permission=True,
    )
    topic = Topic(source.title, "CS", (source,), 10)
    plan = tmp_path / "plan.json"
    plan.write_text(
        '{"privacy_status":"private","entries":['
        '{"kind":"short","source_url":"https://reddit.test/story","privacy_status":"private"},'
        '{"kind":"longform","source_url":"https://reddit.test/story","privacy_status":"private"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda limit: [])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda path: [topic])
    calls = []
    monkeypatch.setattr(cli, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        cli, "run_longform", lambda source_url, output: calls.append({"longform": source_url, "output": output})
    )
    assert cli.run_weekly_production(plan, tmp_path / "output") == 0
    assert calls[0]["force_dry_run"] is True
    assert calls[0]["private_drafts"] is False
    assert calls[0]["youtube_only"] is True
    assert calls[1]["longform"] == source.url


def test_weekly_production_preflights_all_sources_before_rendering(tmp_path, monkeypatch):
    source = Source(
        "Approved story",
        "https://reddit.test/story",
        "A complete story.",
        author="a",
        community="CS",
        reuse_permission=True,
    )
    topic = Topic(source.title, "CS", (source,), 10)
    plan = tmp_path / "plan.json"
    plan.write_text(
        '{"privacy_status":"private","entries":['
        '{"kind":"short","source_url":"https://reddit.test/story","privacy_status":"private"},'
        '{"kind":"short","source_url":"https://reddit.test/missing","privacy_status":"private"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda limit: [])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda path: [topic])
    calls = []
    monkeypatch.setattr(cli, "run", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(ValueError, match="unavailable"):
        cli.run_weekly_production(plan, tmp_path / "output", upload_private=True)
    assert calls == []


def test_weekly_production_rejects_unapproved_longform_source(tmp_path, monkeypatch):
    source = Source("RSS story", "https://example.test/story", "A complete story.")
    topic = Topic(source.title, "CS", (source,), 10)
    plan = tmp_path / "plan.json"
    plan.write_text(
        '{"privacy_status":"private","entries":['
        '{"kind":"longform","source_url":"https://example.test/story","privacy_status":"private"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda limit: [topic])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda path: [])
    with pytest.raises(ValueError, match="not approved"):
        cli.run_weekly_production(plan, tmp_path / "output")
