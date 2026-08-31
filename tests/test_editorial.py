import json
from datetime import date

import pytest

from shorts_pipeline import cli
from shorts_pipeline.editorial import build_editorial_brief, build_research_week
from shorts_pipeline.models import Source, Topic


def _topic(category="AI", permission=False):
    source = Source(
        "Agents fail when the objective is wrong",
        "https://example.test/agents",
        "A source-backed report explains how autonomous systems can act on missing context and spread mistakes quickly.",
        published="Mon, 31 Aug 2026 12:00:00 GMT",
        author="writer" if permission else "",
        community="TalesFromTechSupport" if permission else "",
        reuse_permission=permission,
    )
    return Topic(source.title, category, (source,), 4.2)


def test_editorial_brief_keeps_evidence_and_creative_contract():
    brief = build_editorial_brief(_topic())

    assert brief["source"]["url"] == "https://example.test/agents"
    assert brief["evidence"]["claim"] == _topic().sources[0].summary
    assert brief["creative"]["hook"]
    assert brief["creative"]["format_name"] in {"news_breakdown", "fact_explainer", "question_answer"}
    assert "AI" in brief["creative"]["visual_direction"]
    assert brief["metadata"]["title"]
    assert brief["rights"]["reuse_permission"] is False
    assert brief["longform_bridge"]["question"]


def test_reddit_brief_requires_explicit_reuse_permission():
    topic = _topic(permission=True)
    topic = Topic(
        topic.title,
        "CS",
        (
            Source(
                "A production outage had a surprising cause",
                "https://www.reddit.com/r/TalesFromTechSupport/comments/abc/story",
                "The author describes a complete incident, the debugging steps, and the final outcome.",
                author="writer",
                community="TalesFromTechSupport",
                reuse_permission=False,
            ),
        ),
        topic.score,
    )

    with pytest.raises(ValueError, match="reuse permission"):
        build_editorial_brief(topic)


def test_redd_it_brief_preserves_reddit_rights_gate():
    source = Source(
        "A compact incident outcome",
        "https://redd.it/abc123",
        "The author describes the technical incident, the debugging steps, and the final outcome.",
        author="writer",
        community="sysadmin",
        reuse_permission=True,
    )
    brief = build_editorial_brief(Topic(source.title, "CS", (source,), 2.0))
    assert brief["source"]["type"] == "reddit_anecdote"
    assert brief["rights"]["attribution_required"] is True


def test_research_week_deduplicates_and_reserves_longform():
    topics = [
        Topic(
            "Models become cheaper to run",
            "AI",
            (
                Source(
                    "Models become cheaper to run",
                    "https://example.test/economics",
                    "A source-backed report explains how better infrastructure lowers the cost of useful intelligence for real work.",
                ),
            ),
            2.5,
        ),
        Topic(
            "Defenders catch an agentic attack",
            "Cyber",
            (
                Source(
                    "Defenders catch an agentic attack",
                    "https://example.test/cyber",
                    "A source-backed report explains how defenders detected an AI-assisted attack and contained the affected systems.",
                ),
            ),
            3.5,
        ),
        _topic("AI"),
    ]
    result = build_research_week(topics, date(2026, 9, 7), shorts_count=2, include_longform=True)

    assert result["week_of"] == "2026-09-07"
    assert len(result["shorts"]) == 2
    assert len(result["longform"]) == 1
    assert len({item["source"]["url"] for item in result["shorts"] + result["longform"]}) == 3
    assert all(item["privacy_status"] == "private" for item in result["shorts"] + result["longform"])


def test_research_week_rejects_invalid_count():
    with pytest.raises(ValueError, match="shorts_count"):
        build_research_week([_topic()], date(2026, 9, 7), shorts_count=0)


def test_research_week_rejects_underfilled_short_and_longform_slate():
    with pytest.raises(ValueError, match="at least 3 unique topics"):
        build_research_week([_topic(), _topic("Cyber")], date(2026, 9, 7), shorts_count=2, include_longform=True)


def test_research_command_keeps_ai_ml_and_finance_topics(tmp_path, monkeypatch):
    topics = [
        _topic("AI/ML"),
        Topic(
            "Technology markets move",
            "Finance",
            (
                Source(
                    "Technology markets move",
                    "https://example.test/finance",
                    "A source-backed report explains a technology market development and the measured business result.",
                ),
            ),
            3.0,
        ),
    ]
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: topics)
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])

    assert cli.run_research_week("2026-09-07", 2, tmp_path / "research.json", False) == 0
    payload = json.loads((tmp_path / "research.json").read_text(encoding="utf-8"))
    assert {item["source"]["url"] for item in payload["shorts"]} == {
        "https://example.test/finance",
        "https://example.test/agents",
    }
