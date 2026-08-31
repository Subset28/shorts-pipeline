import json
from datetime import date
from types import SimpleNamespace

import pytest

from shorts_pipeline import cli
from shorts_pipeline.content_calendar import build_weekly_plan
from shorts_pipeline.models import ScriptPackage, Source, Topic


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


def test_weekly_plan_prefers_channel_core_category_for_longform():
    topics = [
        _topic("Aerospace story", "Aerospace", 100),
        _topic("AI story", "AI", 2),
    ]

    plan = build_weekly_plan(
        topics,
        date(2026, 9, 7),
        shorts_count=1,
        include_longform=True,
        longform_topics=topics,
    )

    assert plan[-1]["category"] == "AI"


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


def test_weekly_plan_uses_reference_category_from_experiment_brief():
    topics = [
        _topic("AI story", "AI", 10),
        _topic("CS story", "CS", 9),
        _topic("Cyber story", "Cyber", 8),
    ]
    brief = {
        "status": "ready",
        "experiments": [
            {
                "area": "opening_and_pacing",
                "reference": {"category": "CS", "format_name": "reddit_story"},
                "baseline": {"category": "AI", "format_name": "news_breakdown"},
            }
        ],
    }

    plan = build_weekly_plan(topics, date(2026, 9, 7), shorts_count=3, experiment_brief=brief)

    assert [item["category"] for item in plan] == ["CS", "AI", "Cyber"]
    assert plan[0]["analytics_target"]["role"] == "reference"
    assert plan[0]["analytics_target"]["format_name"] == "reddit_story"
    assert plan[1]["analytics_target"]["role"] == "baseline"


def test_weekly_plan_ignores_incomplete_experiment_brief():
    topic = _topic("AI story", "AI", 10)

    plan = build_weekly_plan(
        [topic], date(2026, 9, 7), shorts_count=1, experiment_brief={"status": "insufficient_sample"}
    )

    assert "analytics_role" not in plan[0]


def test_weekly_plan_does_not_mislabel_same_category_experiment_lanes():
    topic = _topic("AI story", "AI", 10)
    brief = {
        "status": "ready",
        "experiments": [
            {
                "reference": {"category": "AI", "format_name": "fact_explainer", "variant": 0},
                "baseline": {"category": "AI", "format_name": "news_breakdown", "variant": 1},
            }
        ],
    }

    plan = build_weekly_plan([topic], date(2026, 9, 7), shorts_count=1, experiment_brief=brief)

    assert "analytics_target" not in plan[0]


def test_weekly_plan_ignores_malformed_experiment_list():
    topic = _topic("AI story", "AI", 10)

    plan = build_weekly_plan([topic], date(2026, 9, 7), shorts_count=1, experiment_brief={"status": "ready"})

    assert "analytics_target" not in plan[0]


def test_weekly_plan_rejects_missing_explicit_analytics_report(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {"data_dir": tmp_path})())
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: [])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])

    with pytest.raises(ValueError, match="does not exist"):
        cli.run_weekly_plan("2026-09-07", 1, tmp_path / "plan.json", False, tmp_path / "missing.json")


def test_weekly_plan_attaches_private_editorial_research(tmp_path, monkeypatch):
    topic = _topic("AI story", "AI", 10)
    research = tmp_path / "research.json"
    research.write_text(
        '{"privacy_status":"private","shorts":[{"source":{"url":"'
        + topic.sources[0].url
        + '"},"creative":{"hook":"USE THIS"}}],"longform":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type(
            "Settings",
            (),
            {"data_dir": tmp_path, "topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"},
        )(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: [topic])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])

    assert cli.run_weekly_plan("2026-09-07", 1, tmp_path / "plan.json", False, None, research) == 0
    payload = __import__("json").loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert payload["entries"][0]["editorial_brief"]["creative"]["hook"] == "USE THIS"


def test_weekly_plan_rejects_public_editorial_research(tmp_path, monkeypatch):
    research = tmp_path / "research.json"
    research.write_text('{"privacy_status":"public"}', encoding="utf-8")
    with pytest.raises(ValueError, match="private"):
        cli.run_weekly_plan("2026-09-07", 1, tmp_path / "plan.json", False, None, research)


def test_weekly_plan_rejects_malformed_editorial_research(tmp_path):
    research = tmp_path / "research.json"
    research.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        cli.run_weekly_plan("2026-09-07", 1, tmp_path / "plan.json", False, None, research)


def test_weekly_plan_rejects_malformed_editorial_entry(tmp_path):
    research = tmp_path / "research.json"
    research.write_text('{"privacy_status":"private","shorts":[{}],"longform":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="source URL"):
        cli.run_weekly_plan("2026-09-07", 1, tmp_path / "plan.json", False, None, research)


def test_weekly_plan_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="shorts_count"):
        build_weekly_plan([], date(2026, 9, 7), shorts_count=0)


def test_prepare_week_reddit_only_skips_general_discovery(tmp_path, monkeypatch):
    topics = [_topic(f"Reddit story {index}", "Cyber", 10 - index) for index in range(2)]
    settings = SimpleNamespace(
        data_dir=tmp_path,
        topic_limit=10,
        reddit_approved_file=tmp_path / "approved.json",
    )
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: pytest.fail("general discovery was used"))
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: topics)
    monkeypatch.setattr(
        cli,
        "build_research_week",
        lambda selected, *_args: {
            "privacy_status": "private",
            "shorts": [{"source": {"url": topic.sources[0].url}} for topic in selected],
            "longform": [],
        },
    )

    research_path = tmp_path / "research.json"
    plan_path = tmp_path / "plan.json"
    assert cli.run_prepare_week("2026-09-07", 2, research_path, plan_path, False, reddit_only=True) == 0
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert payload["reddit_only"] is True
    assert len(payload["entries"]) == 2
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
        '{"kind":"short","source_url":"https://reddit.test/story","privacy_status":"private",'
        '"publish_at":"2099-01-01T18:00:00+00:00",'
        '"editorial_brief":{"source":{"url":"https://reddit.test/story"}}},'
        '{"kind":"longform","source_url":"https://reddit.test/story","privacy_status":"private",'
        '"publish_at":"2099-01-02T15:00:00+00:00",'
        '"editorial_brief":{"source":{"url":"https://reddit.test/story"}}}]}',
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
        cli,
        "run_longform",
        lambda source_url, output, editorial_brief=None, upload_private=False, publish_at=None: calls.append(
            {
                "longform": source_url,
                "output": output,
                "editorial_brief": editorial_brief,
                "upload_private": upload_private,
                "publish_at": publish_at,
            }
        ),
    )
    assert cli.run_weekly_production(plan, tmp_path / "output") == 0
    assert calls[0]["force_dry_run"] is True
    assert calls[0]["private_drafts"] is False
    assert calls[0]["youtube_only"] is True
    assert calls[0]["publish_at"] == "2099-01-01T18:00:00+00:00"
    assert calls[0]["editorial_brief"]["source"]["url"] == source.url
    assert calls[1]["longform"] == source.url
    assert calls[1]["editorial_brief"]["source"]["url"] == source.url
    assert calls[1]["upload_private"] is False
    assert calls[1]["publish_at"] == "2099-01-02T15:00:00+00:00"


def test_weekly_production_preflight_skips_media_work(tmp_path, monkeypatch):
    source = Source("Approved story", "https://example.test/story", "A complete story.")
    topic = Topic(source.title, "CS", (source,), 10)
    plan = tmp_path / "plan.json"
    plan.write_text(
        '{"privacy_status":"private","entries":[{"kind":"short",'
        '"source_url":"https://example.test/story","privacy_status":"private",'
        '"publish_at":"2099-01-01T18:00:00+00:00"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: type("Settings", (), {"topic_limit": 10, "reddit_approved_file": tmp_path / "approved.json"})(),
    )
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: [topic])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])
    calls = []
    monkeypatch.setattr(cli, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(cli, "run_longform", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert cli.run_weekly_production(plan, tmp_path / "output", preflight_only=True) == 0
    assert calls == []


def test_longform_private_upload_uses_private_youtube_status(tmp_path, monkeypatch):
    source = Source("Long-form source", "https://example.test/longform", "A complete technical account.")
    topic = Topic(source.title, "CS", (source,))
    package = ScriptPackage(
        "Hook", "Narration", "Title", "Description", ["CS"], [source.url], "longform_explainer", "CS"
    )
    settings = SimpleNamespace(
        topic_limit=10,
        reddit_approved_file=tmp_path / "approved.json",
        captions_enabled=False,
        background_dir=tmp_path,
        data_dir=tmp_path,
        youtube_client_secrets=tmp_path / "client.json",
        youtube_token_file=tmp_path / "token.json",
    )
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "discover_topics", lambda _limit: [topic])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda _path: [])
    monkeypatch.setattr(cli, "create_longform_package", lambda _topic, editorial_brief=None: package)
    monkeypatch.setattr(cli, "synthesize", lambda _text, _settings, path: path if path.write_bytes(b"audio") else path)
    monkeypatch.setattr(cli, "_select_backgrounds_for_topic", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        cli,
        "render_longform_video",
        lambda _package, output, *_args: (
            output / "longform.mp4" if (output / "longform.mp4").write_bytes(b"video") else output / "longform.mp4"
        ),
    )
    monkeypatch.setattr(
        cli, "render_thumbnail", lambda _package, path: path if path.write_bytes(b"thumbnail") else path
    )
    monkeypatch.setattr(
        cli,
        "save_manifest",
        lambda *args: (
            tmp_path / "manifest.json"
            if tmp_path.joinpath("manifest.json").write_text(
                json.dumps(
                    {
                        "title": package.title,
                        "description": f"Source: {source.url}",
                        "sources": [source.url],
                        "tags": package.tags,
                        "category": package.category,
                        "format_name": package.format_name,
                        "captions": str(tmp_path / "captions.srt"),
                    }
                )
            )
            else tmp_path / "manifest.json"
        ),
    )
    monkeypatch.setattr(cli, "quality_gate", lambda _path: {})
    monkeypatch.setattr(cli, "load_publish_state", lambda _path: {})
    uploads = []
    monkeypatch.setattr(cli, "upload_youtube", lambda *args: uploads.append(args) or "video-id")
    monkeypatch.setattr(cli, "set_youtube_thumbnail", lambda *args: True)
    monkeypatch.setattr(cli, "record_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "save_publish_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "mark_seen", lambda *args: None)

    assert cli.run_longform(source.url, tmp_path, upload_private=True, publish_at="2099-01-02T15:00:00+00:00") == 0
    assert uploads[0][4] == "private"
    assert uploads[0][5] == "2099-01-02T15:00:00+00:00"


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


def test_weekly_production_allows_discovered_nonreddit_longform_source(tmp_path, monkeypatch):
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
    calls = []
    monkeypatch.setattr(
        cli,
        "run_longform",
        lambda source_url, output, editorial_brief=None, upload_private=False, publish_at=None: calls.append(
            (source_url, output, upload_private, publish_at)
        ),
    )
    assert cli.run_weekly_production(plan, tmp_path / "output") == 0
    assert calls[0][0] == source.url
