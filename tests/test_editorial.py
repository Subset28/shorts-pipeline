import json
from datetime import date

import pytest

from shorts_pipeline import cli
from shorts_pipeline.editorial import apply_editorial_brief, build_editorial_brief, build_research_week
from shorts_pipeline.llm import create_package
from shorts_pipeline.models import Source, Topic
from shorts_pipeline.seo import fallback_package


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


def test_editorial_brief_executes_analytics_treatment():
    target = {
        "area": "packaging",
        "metric": "ctr",
        "role": "reference",
        "change": "Use one clear technical promise.",
        "lane": "AI / news_breakdown",
    }
    brief = build_editorial_brief(_topic(), analytics_target=target)
    assert brief["metadata"]["title"].endswith("| AI explained")
    experiment = brief["creative"]["analytics_experiment"]
    assert experiment["metric"] == "ctr"
    assert experiment["role"] == "reference"
    assert "single-promise" in brief["creative"]["caption_plan"]


def test_editorial_brief_changes_package_metadata_after_validation():
    topic = _topic()
    package = fallback_package(topic)
    brief = build_editorial_brief(topic)
    brief["creative"]["hook"] = "A REVIEWED SOURCE HOOK"
    brief["metadata"]["title"] = "Reviewed source title"

    shaped = apply_editorial_brief(package, topic, brief)

    assert shaped.hook == "A REVIEWED SOURCE HOOK"
    assert shaped.title == "Reviewed source title"
    assert shaped.narration == package.narration


def test_opening_experiment_front_loads_hook_before_source_headline():
    topic = _topic()
    brief = build_editorial_brief(
        topic,
        analytics_target={"area": "opening_and_pacing", "metric": "avg_view_percentage"},
    )
    package = apply_editorial_brief(fallback_package(topic), topic, brief)
    assert package.narration.startswith(package.hook + ".")
    assert topic.sources[0].title in package.narration


def test_create_package_uses_reviewed_brief_without_api_key():
    topic = _topic()
    brief = build_editorial_brief(topic)
    brief["creative"]["hook"] = "REVIEWED HOOK"

    package = create_package(topic, "", "unused", editorial_brief=brief)

    assert package.hook == "REVIEWED HOOK"


def test_editorial_brief_rejects_wrong_source():
    topic = _topic()
    brief = build_editorial_brief(topic)
    brief["source"]["url"] = "https://example.test/other"
    with pytest.raises(ValueError, match="source URL"):
        apply_editorial_brief(fallback_package(topic), topic, brief)


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


def test_research_week_rotates_categories_before_filling_by_score():
    topics = [
        Topic(
            "High score CS incident",
            "CS",
            (
                Source(
                    "High score CS incident",
                    "https://example.test/cs",
                    "A detailed software incident with a measurable outcome.",
                ),
            ),
            100,
        ),
        Topic(
            "AI model on a tiny device",
            "AI/ML",
            (
                Source(
                    "AI model on a tiny device",
                    "https://example.test/ml",
                    "A detailed machine learning result explains the model and its measured outcome.",
                ),
            ),
            10,
        ),
        Topic(
            "Cyber defense catches an attack",
            "Cyber",
            (
                Source(
                    "Cyber defense catches an attack",
                    "https://example.test/cyber",
                    "A detailed defensive security incident explains detection and containment.",
                ),
            ),
            9,
        ),
        Topic(
            "Small model runs locally",
            "AI/ML",
            (
                Source(
                    "Small model runs locally",
                    "https://example.test/ml-2",
                    "A detailed machine learning result explains local inference and its measured outcome.",
                ),
            ),
            7,
        ),
        Topic(
            "Another CS incident",
            "CS",
            (
                Source(
                    "Another CS incident",
                    "https://example.test/cs-2",
                    "A detailed software incident explains the failure and its final outcome.",
                ),
            ),
            8,
        ),
    ]

    result = build_research_week(topics, date(2026, 9, 7), shorts_count=2, include_longform=True)

    assert [item["creative"]["category"] for item in result["shorts"]] == ["AI/ML", "Cyber"]


def test_research_week_applies_analytics_treatment_to_selected_lane():
    result = build_research_week(
        [_topic("AI")],
        date(2026, 9, 7),
        shorts_count=1,
        include_longform=False,
        experiment_brief={
            "status": "ready",
            "experiments": [
                {
                    "area": "opening_and_pacing",
                    "metric": "avg_view_percentage",
                    "change": "Front-load the hook.",
                    "reference": {"category": "AI", "format_name": "news_breakdown", "lane": "AI / news_breakdown"},
                    "baseline": {"category": "CS", "format_name": "fact_explainer", "lane": "CS / fact_explainer"},
                }
            ],
        },
    )
    assert result["shorts"][0]["creative"]["hook"].startswith("The part most people miss:")
    assert result["shorts"][0]["creative"]["analytics_experiment"]["area"] == "opening_and_pacing"


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


def test_prepare_week_writes_private_research_and_plan_once(tmp_path, monkeypatch):
    first = _topic("AI")
    second = _topic("Cyber")
    second = Topic(
        second.title,
        second.category,
        (Source(second.sources[0].title, "https://example.test/cyber", second.sources[0].summary),),
        second.score,
    )
    topics = [first, second]
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    calls = []
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: calls.append("discover") or topics)
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])

    research_path = tmp_path / "research.json"
    plan_path = tmp_path / "plan.json"
    assert cli.run_prepare_week("2026-09-07", 1, research_path, plan_path) == 0
    research = json.loads(research_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert calls == ["discover"]
    assert research["privacy_status"] == "private"
    assert len(research["shorts"]) == 1
    assert len(research["longform"]) == 1
    assert plan["privacy_status"] == "private"
    assert len(plan["entries"]) == 2
    assert all(isinstance(entry.get("editorial_brief"), dict) for entry in plan["entries"])
    assert {entry["source_url"] for entry in plan["entries"]} == {
        item["source"]["url"] for item in research["shorts"] + research["longform"]
    }
