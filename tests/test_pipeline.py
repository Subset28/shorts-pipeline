import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

import shorts_pipeline.cli as cli
from shorts_pipeline.analytics import archive_report, build_report, build_youtube_report, tuning_recommendations
from shorts_pipeline.asset_library import load_asset_manifest, sync_backgrounds
from shorts_pipeline.captions import _escape_ass_text, _write_ass, create_captions, write_speaker_ass
from shorts_pipeline.config import load_settings
from shorts_pipeline.history import load_publish_state, save_publish_state
from shorts_pipeline.longform import create_longform_package, render_longform_video
from shorts_pipeline.media import build_background_reel, select_background, select_backgrounds
from shorts_pipeline.models import ScriptPackage, Source, Topic
from shorts_pipeline.publish import fetch_tiktok_status, metadata, quality_gate, save_manifest, youtube_status
from shorts_pipeline.quality import assess_render
from shorts_pipeline.reddit import (
    _get_with_retries,
    _is_niche_relevant,
    _reddit_quality_score,
    discover_reddit_topics,
    load_approved_reddit_topics,
)
from shorts_pipeline.render import _card, _reddit_post_card, _render_duration
from shorts_pipeline.seo import eligible_formats, fallback_package, normalize_package
from shorts_pipeline.sources import (
    _clean_summary,
    _clean_title,
    _content_key,
    _has_narrative_quality,
    _is_content_mirror,
    is_relevant,
    is_usable_source,
)
from shorts_pipeline.telemetry import record_event
from shorts_pipeline.tts import synthesize


def test_fallback_package_preserves_source_url():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert source.url in package.description
    assert package.sources == [source.url]
    assert "one-minute version" not in package.narration


def test_nonreddit_fallback_opens_with_source_headline_and_lane_takeaway():
    source = Source(
        "A new model passes a difficult evaluation",
        "https://example.test/source",
        "Researchers report a measured improvement on a difficult evaluation. The result is limited to this test.",
    )
    package = fallback_package(Topic(source.title, "ML", (source,)))
    assert package.narration.startswith(source.title + ".")
    assert "The real test is whether the result holds on new data" in package.narration


def test_render_duration_follows_measured_audio(tmp_path, monkeypatch):
    audio = tmp_path / "narration.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(
        "shorts_pipeline.render.subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"stdout": "37.25\n"})(),
    )
    assert _render_duration("short text", audio) == 37.25


def test_render_duration_falls_back_when_audio_probe_fails(tmp_path, monkeypatch):
    audio = tmp_path / "narration.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(
        "shorts_pipeline.render.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("ffprobe unavailable")),
    )
    assert _render_duration("one two three four five six seven eight nine ten", audio) == 10.0


def test_long_form_non_reddit_fallback_keeps_enough_context_for_explainers():
    source = Source(
        "A breakthrough in model safety",
        "https://example.test/safety",
        " ".join(f"Evidence point {index} changes how the model is evaluated." for index in range(30)),
    )
    package = fallback_package(Topic(source.title, "AI News", (source,)))
    assert package.format_name == "news_breakdown"
    assert len(package.narration.split()) >= 100


def test_fallback_package_uses_only_supported_content_lanes():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert package.format_name in {
        "news_breakdown",
        "fact_explainer",
        "myth_bust",
        "technical_joke",
        "surprising_fact",
        "timeline",
        "question_answer",
        "prediction_watch",
    }


def test_finance_topics_get_safe_source_linked_packaging():
    source = Source(
        "A technology market update", "https://example.test/finance", "A company reported a new technology investment."
    )
    package = fallback_package(Topic("A technology market update", "Finance", (source,)))
    assert package.category == "Finance"
    assert "financial advice" in package.description
    assert source.url in package.description


def test_model_output_is_normalized_and_rejects_unsupported_formats():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    topic = Topic("A breakthrough", "AI", (source,))
    package = normalize_package(
        topic,
        {
            "hook": "A strong hook",
            "narration": "This is a sufficiently long narration that explains the source-backed idea in plain language.",
            "title": "A title",
            "description": "An original explanation.",
            "tags": ["AI", "science"],
            "format_name": "news_breakdown",
        },
    )
    assert source.url in package.description
    assert package.sources == [source.url]
    invalid = dict(package.__dict__, format_name="unknown")
    try:
        normalize_package(topic, invalid)
    except ValueError as exc:
        assert "unsupported format" in str(exc)
    else:
        raise AssertionError("unsupported format was accepted")


def test_model_narration_clips_at_a_complete_sentence():
    source = Source(
        "A breakthrough in model safety", "https://example.test/source", "A useful finding with supporting details."
    )
    topic = Topic(source.title, "AI", (source,))
    long_narration = (
        "First, the source reports a measured change. "
        + ("This sentence adds source-backed context. " * 30)
        + "The takeaway is to check the evidence."
    )
    package = normalize_package(
        topic,
        {
            "hook": "A strong hook",
            "narration": long_narration,
            "title": "A title",
            "description": "An original explanation.",
            "tags": ["AI"],
            "format_name": "news_breakdown",
        },
    )
    assert len(package.narration) <= 900
    assert package.narration.endswith("context.")


def test_metadata_is_platform_neutral():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    data = metadata(fallback_package(Topic("A breakthrough", "AI", (source,))))
    assert set(data) == {"title", "description", "tags", "sources", "format_name", "category", "variant"}
    assert data["category"] == "AI"


def test_metadata_description_is_youtube_safe():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    package.description = "Valid\x00 description\u2028 – café"
    assert metadata(package)["description"] == "Valid description cafe"
    package.description = "A *marked* > description"
    assert metadata(package)["description"] == "A marked  description"


def test_scheduled_youtube_upload_is_private_until_publish_time():
    status = youtube_status("public", "2099-01-02T15:04:05Z")
    assert status == {"privacyStatus": "private", "publishAt": "2099-01-02T15:04:05Z", "selfDeclaredMadeForKids": False}


def test_variants_rotate_content_lane_without_changing_source():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    first = fallback_package(Topic("A breakthrough", "AI", (source,)), variant=0)
    second = fallback_package(Topic("A breakthrough", "AI", (source,)), variant=1)
    assert first.sources == second.sources == [source.url]
    assert first.variant == 0
    assert second.variant == 1
    assert first.format_name in eligible_formats(Topic("A breakthrough", "AI", (source,)))
    assert second.format_name in eligible_formats(Topic("A breakthrough", "AI", (source,)))
    assert (
        len({fallback_package(Topic("A breakthrough", "AI", (source,)), variant=i).format_name for i in range(4)}) >= 2
    )


def test_fallback_hooks_match_the_source_headline():
    source = Source(
        "A breakthrough in model safety", "https://example.test/safety", "A useful finding with supporting details."
    )
    topic = Topic(source.title, "AI", (source,))
    for variant in range(4):
        package = fallback_package(topic, variant=variant)
        assert "breakthrough" in package.hook.lower()
        assert "behind ai" not in package.hook.lower()
        assert len(package.hook) <= 100


def test_unsupported_timeline_or_prediction_is_rejected_for_plain_source():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding with supporting details only.")
    topic = Topic("A breakthrough", "AI", (source,))
    assert "timeline" not in eligible_formats(topic)
    assert "prediction_watch" not in eligible_formats(topic)
    data = {
        "hook": "A hook",
        "narration": "This is a sufficiently long narration that explains the source-backed idea in plain language.",
        "title": "A title",
        "description": "An explanation.",
        "tags": [],
        "format_name": "timeline",
    }
    try:
        normalize_package(topic, data)
    except ValueError as exc:
        assert "unsupported format" in str(exc)
    else:
        raise AssertionError("ineligible timeline format was accepted")


def test_specialized_lanes_require_a_real_source_signal():
    source = Source(
        "A first launch could change the market",
        "https://example.test/story",
        "The team announced a first launch and expects a 20% improvement after testing.",
    )
    topic = Topic("A first launch could change the market", "AI", (source,))
    formats = eligible_formats(topic)
    assert {"surprising_fact", "timeline", "prediction_watch"}.issubset(formats)
    package = fallback_package(topic, variant=5)
    assert package.format_name in formats
    assert source.title.split()[0] in package.hook


def test_plain_source_keeps_only_universal_watchable_lanes():
    source = Source("A useful finding", "https://example.test/plain", "A useful finding with supporting details.")
    formats = eligible_formats(Topic("A useful finding", "AI", (source,)))
    assert formats == ("news_breakdown", "fact_explainer", "technical_joke", "question_answer")


def test_joke_lane_is_limited_to_audiences_where_it_fits_naturally():
    source = Source(
        "Why spacecraft use staging", "https://example.test/rocket", "Dropping empty mass improves the next burn."
    )
    formats = eligible_formats(Topic(source.title, "Aerospace", (source,)))
    assert "technical_joke" not in formats


def test_reddit_story_lane_requires_explicit_rights_and_attribution():
    source = Source(
        "A developer's production incident",
        "https://www.reddit.com/r/programming/comments/example/story/",
        "A developer describes an overnight production incident and the lesson learned. "
        "The cleanup script matched the live hostname, the service went down, and the "
        "team restored a backup before adding a second-person approval step to every "
        "deployment. The author says the new safeguard has prevented a repeat.",
        author="example_user",
        community="programming",
        reuse_permission=True,
    )
    topic = Topic(source.title, "CS", (source,))
    assert "reddit_story" in eligible_formats(topic)
    assert fallback_package(topic).format_name == "reddit_story"
    packages = [fallback_package(topic, variant=i) for i in range(len(eligible_formats(topic)))]
    package = next(item for item in packages if item.format_name == "reddit_story")
    assert source.title in package.narration
    assert "The cleanup script matched the live hostname" in package.narration
    assert package.narration.endswith("The author says the new safeguard has prevented a repeat.")
    assert package.narration.startswith(f"{source.title}. ")
    assert package.card_text.startswith(source.title)
    assert "Here's how it unfolded" in package.narration
    assert "example_user" not in package.narration
    assert "u/example_user" in package.description

    unapproved = Source(source.title, source.url, source.summary, author="example_user", community="programming")
    assert "reddit_story" not in eligible_formats(Topic(unapproved.title, "CS", (unapproved,)))


def test_reddit_discovery_candidates_are_not_automatically_cleared(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return (
                {"access_token": "token"}
                if self.token
                else {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "title": "A production incident",
                                    "selftext": "A detailed account " + "with useful context " * 30,
                                    "author": "story_author",
                                    "permalink": "/r/programming/comments/abc/story/",
                                    "subreddit": "programming",
                                    "score": 123,
                                }
                            }
                        ]
                    }
                }
            )

        def __init__(self, token=False):
            self.token = token

    class Client:
        def __init__(self, **kwargs):
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return Response(token=True)

        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("shorts_pipeline.reddit.httpx.Client", Client)
    topics = discover_reddit_topics(("programming",), "id", "secret", "test-agent", 1)
    source = topics[0].sources[0]
    assert source.author == "story_author"
    assert source.reuse_permission is False


def test_generic_reddit_prompts_must_match_a_channel_topic():
    assert _is_niche_relevant("AskReddit", "What is your favorite meal?", "I love pasta.") is False
    assert (
        _is_niche_relevant("AskReddit", "What was your worst server outage?", "The database failed overnight.") is True
    )
    assert _is_niche_relevant("TalesFromTechSupport", "My strangest ticket", "The printer became sentient.") is True


def test_reddit_quality_prefers_specific_story_arcs_over_generic_high_scores():
    strong = Source(
        "Our deploy deleted production data",
        "https://www.reddit.com/r/sysadmin/comments/strong/story/",
        "The deployment failed after a permission change. We restored the backup, traced the error, and added a second-person approval step.",
        author="author",
        community="sysadmin",
        reuse_permission=True,
    )
    weak = Source(
        "Does anyone else feel burned out?",
        "https://www.reddit.com/r/sysadmin/comments/weak/story/",
        "Work has been stressful lately and I am tired.",
        author="author",
        community="sysadmin",
        reuse_permission=True,
    )
    assert _reddit_quality_score(Topic(strong.title, "CS", (strong,), 100)) > _reddit_quality_score(
        Topic(weak.title, "CS", (weak,), 1000)
    )


def test_reddit_fetch_retries_transient_request_errors(monkeypatch):
    class Client:
        def __init__(self):
            self.calls = 0

        def get(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls < 3:
                raise httpx.RequestError("temporary network failure")
            return SimpleNamespace(status_code=200, raise_for_status=lambda: None)

    client = Client()
    monkeypatch.setattr("shorts_pipeline.reddit.time.sleep", lambda _delay: None)
    response = _get_with_retries(client, "https://example.test", {})
    assert response is not None
    assert client.calls == 3


def test_private_draft_reddit_worker_keeps_polling_without_approved_queue(monkeypatch):
    class StopLoop(BaseException):
        pass

    calls = []
    monkeypatch.setattr(cli, "load_settings", lambda: object())
    monkeypatch.setattr(cli, "_has_unseen_reddit_topic", lambda _settings: False)

    def fake_run(**kwargs):
        calls.append(kwargs)
        raise StopLoop()

    monkeypatch.setattr(cli, "run", fake_run)
    with pytest.raises(StopLoop):
        cli.run_worker(reddit_only=True, private_drafts=True)
    assert calls == [{"force_dry_run": False, "reddit_only": True, "private_drafts": True, "youtube_only": False}]


def test_longform_package_has_argument_structure_and_source_link():
    source = Source(
        "A production incident",
        "https://www.reddit.com/r/sysadmin/comments/example/story/",
        "The deployment failed. The team restored a backup and added a safeguard.",
        author="author",
        community="sysadmin",
        reuse_permission=True,
    )
    package = create_longform_package(Topic(source.title, "CS", (source,)))
    assert package.format_name == "longform_explainer"


def test_longform_render_writes_video_with_audio_and_captions(tmp_path, monkeypatch):
    source = Source("A technical incident", "https://example.test/source", "A detailed technical report.")
    package = create_longform_package(Topic(source.title, "CS", (source,)))
    audio = tmp_path / "audio.mp3"
    captions = tmp_path / "captions.srt"
    audio.write_bytes(b"audio")
    captions.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr("shorts_pipeline.longform.shutil.which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr("shorts_pipeline.longform.subprocess.run", lambda command, **kwargs: calls.append(command))
    output = render_longform_video(package, tmp_path, audio, captions, None)
    assert output.name == "longform.mp4"
    assert "2:a" in calls[0]
    assert all(
        section in package.narration for section in ("Context:", "What happened:", "Why it matters:", "Takeaway:")
    )
    assert source.url in package.description


def test_nonreddit_transparent_hook_card_has_high_contrast_opening(tmp_path):
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    output = tmp_path / "card.png"
    _card(package, output, transparent=True)
    image = Image.open(output).convert("RGBA")
    assert image.size == (1080, 1920)
    assert image.getpixel((50, 180))[3] > 0
    assert image.getpixel((75, 215))[3] > 0


def test_reddit_loader_only_returns_explicitly_approved_candidates(tmp_path):
    path = tmp_path / "reddit.json"
    source = {
        "title": "A production incident",
        "url": "https://www.reddit.com/r/programming/comments/abc/story/",
        "summary": "A detailed account with useful context " * 12,
        "author": "story_author",
        "community": "programming",
        "reuse_permission": False,
    }
    path.write_text(
        json.dumps([{"source": source}, {"source": {**source, "reuse_permission": True}}]), encoding="utf-8"
    )
    topics = load_approved_reddit_topics(path)
    assert len(topics) == 1
    assert topics[0].sources[0].reuse_permission is True
    assert topics[0].category == "CS"


def test_variant_publish_state_keys_are_isolated_but_legacy_default_survives():
    assert cli._publish_state_key("https://example.test/source", 0) == "https://example.test/source"
    assert cli._publish_state_key("https://example.test/source", 1) == "https://example.test/source#variant=1"


def test_youtube_only_mode_skips_tiktok():
    assert cli._should_upload_tiktok(private_drafts=False, youtube_only=True) is False
    assert cli._should_upload_tiktok(private_drafts=False, youtube_only=False) is True
    assert cli._should_upload_tiktok(private_drafts=True, youtube_only=False) is False


def test_youtube_upload_limit_errors_are_classified_for_worker_backoff():
    assert cli.is_youtube_upload_limit_error(RuntimeError("uploadLimitExceeded")) is True
    assert cli.is_youtube_upload_limit_error(RuntimeError("network unavailable")) is False


def test_publish_state_resumes_each_platform_without_overwriting(tmp_path):
    path = tmp_path / "publish_state.json"
    save_publish_state(path, "https://example.test/source", youtube_id="yt123")
    save_publish_state(path, "https://example.test/source", tiktok_id="tt456")
    assert load_publish_state(path)["https://example.test/source"] == {"tiktok_id": "tt456", "youtube_id": "yt123"}


def test_tiktok_status_fetch_reads_completion(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"error": {"code": "ok"}, "data": {"status": "PUBLISH_COMPLETE"}}

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("shorts_pipeline.publish.httpx.Client", lambda **kwargs: Client())
    assert fetch_tiktok_status("token", "publish-id") == "PUBLISH_COMPLETE"


def test_captions_fallback_writes_srt_without_whisper(tmp_path, monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", None)
    output = create_captions("One two three four five six seven eight.", None, tmp_path / "captions.srt")
    assert output and output.exists()
    assert "00:00:00,000 -->" in output.read_text(encoding="utf-8-sig")


def test_speaker_captions_assign_distinct_colors_and_readable_size(tmp_path):
    output = write_speaker_ass(
        [
            {"start": 0, "end": 1, "text": "First speaker", "speaker": "SPEAKER_00"},
            {"start": 1, "end": 2, "text": "Second speaker", "speaker": "SPEAKER_01"},
        ],
        tmp_path / "captions.ass",
    )
    content = output.read_text(encoding="utf-8")
    assert "Speaker0,Arial,68,&H0000D7FF" in content
    assert "Speaker1,Arial,68,&H0000FF80" in content
    assert r"{\fad(70,45)\blur1\t(0,120,\blur0)" in content
    assert "Speaker0,,0,0,0,," in content and "FIRST SPEAKER" in content
    assert "Speaker1,,0,0,0,," in content and "SECOND SPEAKER" in content


def test_standard_captions_use_large_animated_three_word_beats(tmp_path):
    output = _write_ass([(0, 1, "One two three four")], tmp_path / "captions.ass")
    content = output.read_text(encoding="utf-8")
    assert r"{\fad(70,45)\blur1" in content
    assert "Style: Default,Arial,68,&H00FFFFFF" in content
    assert "ONE TWO THREE\\NFOUR" in content


def test_ass_caption_text_escapes_formatting_control_characters():
    assert _escape_ass_text(r"Try {this}\\path") == r"Try \{this\}\\\\path"


def test_create_captions_uses_opt_in_speaker_path(tmp_path, monkeypatch):
    audio = tmp_path / "narration.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setenv("WHISPERX_DIARIZATION", "true")
    monkeypatch.setattr(
        "shorts_pipeline.captions._whisperx_speaker_segments",
        lambda *_args: [
            {"start": 0, "end": 1, "text": "First speaker", "speaker": "SPEAKER_00"},
            {"start": 1, "end": 2, "text": "Second speaker", "speaker": "SPEAKER_01"},
        ],
    )
    output = create_captions("unused", audio, tmp_path / "captions.srt")
    assert output and output.exists()
    assert "Speaker1,Arial,68" in output.with_suffix(".ass").read_text(encoding="utf-8")


def test_telemetry_is_append_only_and_secret_free(tmp_path):
    path = tmp_path / "events.jsonl"
    record_event(path, "draft_created", format_name="news_breakdown", source_url="https://example.test")
    record_event(path, "youtube_published", platform_id="abc")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == ["draft_created", "youtube_published"]
    assert "api_key" not in rows[0]


def test_background_selection_is_stable_and_uses_fallback(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    chosen = select_background(tmp_path, "https://example.test/topic")
    assert chosen in {first, second}
    assert select_background(tmp_path, "https://example.test/topic") == chosen

    empty = tmp_path / "empty"
    fallback = tmp_path / "fallback.mp4"
    fallback.write_bytes(b"fallback")
    assert select_background(empty, "topic", fallback) == fallback


def test_analytics_joins_platform_metrics_to_experiment_metadata(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "event": "draft_created",
                "source_url": "https://example.test/source",
                "category": "AI",
                "format_name": "news_breakdown",
                "title": "A title",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    metrics = tmp_path / "metrics.csv"
    metrics.write_text(
        "source_url,platform,views,likes,comments,shares\nhttps://example.test/source,youtube,1000,50,10,5\nhttps://missing.test, tiktok, 4, 1, 0, 0\n",
        encoding="utf-8",
    )
    report = build_report(events, metrics)
    assert report["matched_rows"] == 1
    assert report["unmatched_rows"] == 1
    assert report["rows"][0]["views"] == 1000
    assert report["rows"][0]["engagement_rate"] == 0.065


def test_analytics_keeps_variants_separate(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "draft_created",
                        "source_url": "https://example.test/source",
                        "category": "AI",
                        "format_name": "myth_bust",
                        "variant": 0,
                    }
                ),
                json.dumps(
                    {
                        "event": "draft_created",
                        "source_url": "https://example.test/source",
                        "category": "AI",
                        "format_name": "technical_joke",
                        "variant": 1,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    metrics = tmp_path / "metrics.csv"
    metrics.write_text(
        "source_url,platform,variant,views\nhttps://example.test/source,youtube,0,100\nhttps://example.test/source,youtube,1,200\n",
        encoding="utf-8",
    )
    report = build_report(events, metrics)
    assert report["matched_rows"] == 2
    assert {row["variant"] for row in report["rows"]} == {0, 1}


def test_tuning_recommendations_require_repeated_evidence():
    report = {
        "rows": [
            {
                "category": "AI",
                "format_name": "fact_explainer",
                "videos": 3,
                "avg_views": 1000,
                "engagement_rate": 0.02,
            },
            {
                "category": "Cyber",
                "format_name": "news_breakdown",
                "videos": 1,
                "avg_views": 5000,
                "engagement_rate": 0.09,
            },
        ]
    }
    recommendations = tuning_recommendations(report)
    assert any("AI" in item and "fact_explainer" in item for item in recommendations)
    assert all("Cyber" not in item for item in recommendations)


def test_tuning_recommendations_call_out_insufficient_sample_size():
    assert tuning_recommendations({"rows": []}) == [
        "Collect at least two videos per lane before changing the content mix."
    ]


def test_archive_report_keeps_only_aggregate_tuning_data(tmp_path):
    output = archive_report(
        {
            "rows": [{"category": "AI", "videos": 2, "source_url": "https://private.example"}],
            "recommendations": ["Keep testing AI."],
        },
        tmp_path / "weekly.json",
        "2026-08-30",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {
        "week_of": "2026-08-30",
        "rows": [{"category": "AI", "videos": 2}],
        "recommendations": ["Keep testing AI."],
    }


def test_build_youtube_report_uses_latest_snapshot_per_video():
    report = build_youtube_report(
        {
            "snapshots": [
                {
                    "video_id": "a",
                    "category": "AI",
                    "format_name": "fact_explainer",
                    "collected_at": "2026-08-30T01:00:00+00:00",
                    "metrics": {"views": 10, "likes": 1},
                },
                {
                    "video_id": "a",
                    "category": "AI",
                    "format_name": "fact_explainer",
                    "collected_at": "2026-08-30T02:00:00+00:00",
                    "metrics": {"views": 20, "likes": 2},
                },
            ]
        }
    )
    assert report["rows"][0]["videos"] == 1
    assert report["rows"][0]["views"] == 20


def test_background_manifest_requires_provenance_fields(tmp_path):
    manifest = tmp_path / "backgrounds.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "name": "x",
                        "filename": "x.mp4",
                        "url": "https://example.test/x.mp4",
                        "source_page": "https://example.test",
                        "attribution": "Example",
                        "rights_note": "authorized",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_asset_manifest(manifest)[0]["name"] == "x"


def test_background_sync_uses_isolated_temporary_download_path(tmp_path, monkeypatch):
    manifest = tmp_path / "backgrounds.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "name": "x",
                        "filename": "x.mp4",
                        "url": "https://example.test/x.mp4",
                        "source_page": "https://example.test",
                        "attribution": "Example",
                        "rights_note": "authorized",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"video"

    monkeypatch.setattr("shorts_pipeline.asset_library.httpx.stream", lambda *args, **kwargs: Response())
    paths = sync_backgrounds(manifest, tmp_path / "out")
    assert paths[0].read_bytes() == b"video"
    assert not list((tmp_path / "out").glob("*.part"))


def test_manifest_records_selected_background(tmp_path):
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    background = tmp_path / "background.mp4"
    background.write_bytes(b"video")
    manifest = save_manifest(
        fallback_package(Topic("A breakthrough", "AI", (source,))), tmp_path / "short.mp4", tmp_path, background
    )
    assert json.loads(manifest.read_text(encoding="utf-8"))["background"] == str(background)


def test_manifest_records_audio_and_caption_paths(tmp_path):
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    audio = tmp_path / "audio.mp3"
    captions = tmp_path / "captions.srt"
    manifest = save_manifest(
        fallback_package(Topic("A breakthrough", "AI", (source,))),
        tmp_path / "short.mp4",
        tmp_path,
        audio=audio,
        captions=captions,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["audio"] == str(audio)
    assert payload["captions"] == str(captions)


def test_quality_gate_rejects_failed_render(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"quality": {"passed": False, "issues": ["audio_video_duration_mismatch"]}}), encoding="utf-8"
    )
    try:
        quality_gate(manifest)
    except RuntimeError as exc:
        assert "audio_video_duration_mismatch" in str(exc)
    else:
        raise AssertionError("failed render quality was accepted")


def test_quality_gate_accepts_passing_render(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"quality": {"passed": True, "issues": []}}), encoding="utf-8")
    assert quality_gate(manifest)["passed"] is True


def test_tts_does_not_reuse_stale_audio_after_provider_failure(tmp_path, monkeypatch):
    output = tmp_path / "narration.mp3"
    output.write_bytes(b"old narration")
    settings = SimpleNamespace(
        elevenlabs_voice_id="",
        elevenlabs_rotator_path=tmp_path / "missing-rotator.py",
        edge_tts_voice="en-US-GuyNeural",
    )

    def fail(*_args, **_kwargs):
        raise OSError("provider unavailable")

    monkeypatch.setattr("shorts_pipeline.tts.subprocess.run", fail)
    assert synthesize("new narration", settings, output) is None
    assert not output.exists()


def test_quality_report_records_sync_and_caption_coverage(tmp_path, monkeypatch):
    video = tmp_path / "short.mp4"
    audio = tmp_path / "narration.mp3"
    background = tmp_path / "background.mp4"
    captions = tmp_path / "captions.srt"
    for path in (video, audio, background):
        path.write_bytes(b"media")
    captions.write_text("1\n00:00:00,000 --> 00:00:09,500\nWORDS\n", encoding="utf-8")
    durations = {video: 10.0, audio: 10.0, background: 60.0}
    monkeypatch.setattr("shorts_pipeline.quality.probe_duration", lambda path: durations.get(path))
    report = assess_render(video, audio, captions, background)
    assert report["passed"] is True
    assert report["audio_video_delta_seconds"] == 0.0
    assert report["caption_coverage"] == 0.95


def test_quality_report_flags_background_and_caption_failures(tmp_path, monkeypatch):
    video = tmp_path / "short.mp4"
    audio = tmp_path / "narration.mp3"
    background = tmp_path / "background.mp4"
    captions = tmp_path / "captions.srt"
    for path in (video, audio, background):
        path.write_bytes(b"media")
    captions.write_text("1\n00:00:00,000 --> 00:00:02,000\nWORDS\n", encoding="utf-8")
    durations = {video: 10.0, audio: 10.5, background: 8.0}
    monkeypatch.setattr("shorts_pipeline.quality.probe_duration", lambda path: durations.get(path))
    report = assess_render(video, audio, captions, background)
    assert report["passed"] is False
    assert {"audio_video_duration_mismatch", "background_shorter_than_video", "captions_end_too_early"}.issubset(
        report["issues"]
    )


def test_background_reel_selection_rotates_stably(tmp_path):
    for name in ("a.mp4", "b.mp4", "c.mp4"):
        (tmp_path / name).write_bytes(name.encode())
    selected = select_backgrounds(tmp_path, "https://example.test/topic")
    assert len(selected) == 3
    assert selected == select_backgrounds(tmp_path, "https://example.test/topic")
    assert {path.name for path in selected} == {"a.mp4", "b.mp4", "c.mp4"}


def test_background_reel_builds_long_sequence_instead_of_short_loop(tmp_path, monkeypatch):
    sources = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    for source in sources:
        source.write_bytes(b"video")
    captured = {}
    monkeypatch.setattr("shorts_pipeline.media.shutil.which", lambda name: "ffmpeg")

    def fake_run(command, **kwargs):
        captured["command"] = command
        return None

    monkeypatch.setattr("shorts_pipeline.media.subprocess.run", fake_run)
    result = build_background_reel(sources, tmp_path / "reel.mp4", duration=60, variation_key="demo")
    assert result == tmp_path / "reel.mp4"
    command = captured["command"]
    assert command.count("-i") == 22
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "xfade=transition=fade:duration=0.180" in filter_graph
    assert "sin(2*PI*t/3.000)" in filter_graph
    assert command[command.index("-map") + 1] == "[x21]"


def test_background_selection_maps_editorial_aliases_to_asset_categories(tmp_path):
    for name in ("ai.mp4", "cyber.mp4", "general.mp4", "rocket.mp4"):
        (tmp_path / name).write_bytes(name.encode())
    manifest = tmp_path / "backgrounds.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {"filename": "ai.mp4", "category": "AI"},
                    {"filename": "cyber.mp4", "category": "Cybersecurity"},
                    {"filename": "general.mp4", "category": "General"},
                    {"filename": "rocket.mp4", "category": "Aerospace"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert {path.name for path in select_backgrounds(tmp_path, "ai-key", category="AI News", manifest=manifest)} == {
        "ai.mp4"
    }
    assert {path.name for path in select_backgrounds(tmp_path, "cyber-key", category="Cyber", manifest=manifest)} == {
        "cyber.mp4"
    }
    assert {
        path.name for path in select_backgrounds(tmp_path, "finance-key", category="Finance", manifest=manifest)
    } == {"general.mp4"}


def test_reddit_background_directory_is_configurable(monkeypatch):
    monkeypatch.setenv("REDDIT_BACKGROUND_DIR", "data/backgrounds/reddit")
    assert load_settings().reddit_background_dir == Path("data/backgrounds/reddit")


def test_cli_background_selection_passes_configured_manifest(tmp_path, monkeypatch):
    manifest = tmp_path / "backgrounds.json"
    settings = type("Settings", (), {"background_manifest": manifest})()
    captured = {}

    def fake_select(directory, key, **kwargs):
        captured.update(directory=directory, key=key, kwargs=kwargs)
        return []

    monkeypatch.setattr(cli, "select_backgrounds", fake_select)
    assert cli._select_backgrounds_for_topic(settings, tmp_path, "topic", "AI News", "source") == []
    assert captured["kwargs"]["manifest"] == manifest
    assert captured["kwargs"]["category"] == "AI News"


def test_dockerfile_copies_asset_manifest():
    dockerfile = Path(__file__).parents[1] / "Dockerfile"
    assert "COPY assets ./assets" in dockerfile.read_text(encoding="utf-8")


def test_nas_deploy_script_preserves_remote_environment():
    script = Path(__file__).parents[1] / "scripts" / "deploy-nas.ps1"
    text = script.read_text(encoding="utf-8")
    assert "scp -O" in text
    assert "cp -n .env.example .env" in text
    assert "keys.json" not in text
    assert 'Filter "user_*.mp4"' in text


def test_feed_summary_removes_markup_urls_and_link_aggregator_boilerplate():
    cleaned = _clean_summary(
        '<p>Article URL: <a href="https://example.test">https://example.test</a></p><p>Points: 27</p># Comments: 11'
    )
    assert cleaned == ""


def test_feed_summary_removes_newsletter_boilerplate_but_keeps_story():
    cleaned = _clean_summary(
        "This is today’s edition of The Download, our weekday newsletter that provides a daily dose of what’s going on in the world of technology. A startup claims it found a new model."
    )
    assert cleaned == "A startup claims it found a new model"


def test_fallback_narration_uses_title_when_summary_is_feed_boilerplate():
    source = Source("A useful machine-learning discovery", "https://example.test/source", "27")
    package = fallback_package(Topic("A useful machine-learning discovery", "ML", (source,)))
    assert "A useful machine-learning discovery" in package.narration
    assert "https://" not in package.narration


def test_discovery_rejects_off_topic_items_for_audience_lanes():
    drought = Source("Europe's summer drought", "https://example.test/drought", "Rivers and soil are unusually dry.")
    software = Source(
        "A new compiler improves code",
        "https://example.test/compiler",
        "The developer tool changes how software is built.",
    )
    assert not is_relevant("CS", drought)
    assert is_relevant("CS", software)


def test_discovery_rejects_generic_or_underdescribed_feed_titles():
    generic = Source("Markets - Bloomberg.com", "https://example.test/markets", "")
    thin = Source("AI update", "https://example.test/ai", "A short note.")
    useful = Source(
        "How a new compiler improves code",
        "https://example.test/compiler",
        "A developer tool changes how software is built.",
    )
    assert not is_usable_source(generic)
    assert not is_usable_source(thin)
    assert is_usable_source(useful)


def test_discovery_requires_lane_specific_narrative_quality():
    thin_finance = Source(
        "Tech stocks rally",
        "https://example.test/markets",
        "Stocks rose after earnings beat estimates and investors reacted.",
    )
    ceremony = Source(
        "Ribbon-Cutting Event for a New Facility",
        "https://example.test/event",
        "Officials attended a ceremony and gave remarks to the audience. " * 5,
    )
    useful_finance = Source(
        "How AI spending changed the market",
        "https://example.test/market-story",
        "The company changed its AI spending plan after revenue missed expectations. " * 6,
    )
    assert not _has_narrative_quality("Finance", thin_finance)
    assert not _has_narrative_quality("Aerospace", ceremony)
    assert _has_narrative_quality("Finance", useful_finance)


def test_content_key_deduplicates_newsletter_and_article_mirrors():
    first = Source(
        "The Download: AI story",
        "https://example.test/newsletter",
        "The same story explains how agents changed their behavior during training. More context follows.",
    )
    mirror = Source(
        "Inside the AI story",
        "https://example.test/article",
        "The same story explains how agents changed their behavior during training. More context follows.",
    )
    different = Source(
        "A different AI story",
        "https://example.test/other",
        "A separate report describes a different model and a different result.",
    )
    assert _content_key(first) == _content_key(mirror)
    assert _content_key(first) != _content_key(different)
    assert _is_content_mirror(mirror, [first])
    assert not _is_content_mirror(different, [first])


def test_newsletter_title_matches_the_lead_story():
    assert _clean_title("The Download: inside OpenAI's hack, and a new EV takes on the US") == "inside OpenAI's hack"
    assert _clean_title("A normal AI and robotics headline") == "A normal AI and robotics headline"


def test_batch_reports_feed_outage_before_claiming_topics_are_seen(monkeypatch):
    monkeypatch.setattr(cli, "discover_topics", lambda limit: [])
    monkeypatch.setattr(cli, "load_approved_reddit_topics", lambda path: [])
    try:
        cli.run_batch(1, force_dry_run=True)
    except RuntimeError as exc:
        assert "RSS feeds may be unavailable" in str(exc)
    else:
        raise AssertionError("empty discovery did not report a feed outage")


def test_reddit_card_generates_animated_award_loop(tmp_path):
    package = ScriptPackage(
        hook="A hook",
        narration="Here's what happened: A coworker made an outrageous request. The useful part is what happened next.",
        title="A coworker made an outrageous request",
        description="Reddit attribution: u/example in r/test",
        sources=["https://www.reddit.com/r/test/comments/example/"],
        format_name="reddit_story",
        category="Reddit Stories",
    )
    card = tmp_path / "reddit-card.png"
    _reddit_post_card(package, card)
    assert card.exists()
    with Image.open(card.with_suffix(".gif")) as animated:
        assert animated.size == (1080, 1920)
        assert animated.n_frames == 8
