from shorts_pipeline.models import Source, Topic
from shorts_pipeline.history import load_publish_state, save_publish_state
from shorts_pipeline.captions import create_captions
from shorts_pipeline.telemetry import record_event
import json
from shorts_pipeline.publish import fetch_tiktok_status, metadata
from shorts_pipeline.seo import fallback_package, normalize_package
from shorts_pipeline.media import select_background, select_backgrounds
from shorts_pipeline.analytics import build_report
from shorts_pipeline.asset_library import load_asset_manifest
from shorts_pipeline.publish import save_manifest
from pathlib import Path
from shorts_pipeline.sources import _clean_summary
import shorts_pipeline.cli as cli


def test_fallback_package_preserves_source_url():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert source.url in package.description
    assert package.sources == [source.url]


def test_fallback_package_uses_only_supported_content_lanes():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert package.format_name in {"news_breakdown", "fact_explainer", "myth_bust", "technical_joke"}


def test_model_output_is_normalized_and_rejects_unsupported_formats():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    topic = Topic("A breakthrough", "AI", (source,))
    package = normalize_package(topic, {
        "hook": "A strong hook",
        "narration": "This is a sufficiently long narration that explains the source-backed idea in plain language.",
        "title": "A title",
        "description": "An original explanation.",
        "tags": ["AI", "science"],
        "format_name": "news_breakdown",
    })
    assert source.url in package.description
    assert package.sources == [source.url]
    invalid = dict(package.__dict__, format_name="unknown")
    try:
        normalize_package(topic, invalid)
    except ValueError as exc:
        assert "unsupported format" in str(exc)
    else:
        raise AssertionError("unsupported format was accepted")


def test_metadata_is_platform_neutral():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    data = metadata(fallback_package(Topic("A breakthrough", "AI", (source,))))
    assert set(data) == {"title", "description", "tags", "sources", "format_name", "category", "variant"}
    assert data["category"] == "AI"


def test_variants_rotate_content_lane_without_changing_source():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    first = fallback_package(Topic("A breakthrough", "AI", (source,)), variant=0)
    second = fallback_package(Topic("A breakthrough", "AI", (source,)), variant=1)
    assert first.sources == second.sources == [source.url]
    assert first.variant == 0
    assert second.variant == 1
    assert first.format_name != second.format_name


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
    events.write_text(json.dumps({"event": "draft_created", "source_url": "https://example.test/source", "category": "AI", "format_name": "news_breakdown", "title": "A title"}) + "\n", encoding="utf-8")
    metrics = tmp_path / "metrics.csv"
    metrics.write_text("source_url,platform,views,likes,comments,shares\nhttps://example.test/source,youtube,1000,50,10,5\nhttps://missing.test, tiktok, 4, 1, 0, 0\n", encoding="utf-8")
    report = build_report(events, metrics)
    assert report["matched_rows"] == 1
    assert report["unmatched_rows"] == 1
    assert report["rows"][0]["views"] == 1000
    assert report["rows"][0]["engagement_rate"] == 0.065


def test_analytics_keeps_variants_separate(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join([
            json.dumps({"event": "draft_created", "source_url": "https://example.test/source", "category": "AI", "format_name": "myth_bust", "variant": 0}),
            json.dumps({"event": "draft_created", "source_url": "https://example.test/source", "category": "AI", "format_name": "technical_joke", "variant": 1}),
        ]) + "\n",
        encoding="utf-8",
    )
    metrics = tmp_path / "metrics.csv"
    metrics.write_text("source_url,platform,variant,views\nhttps://example.test/source,youtube,0,100\nhttps://example.test/source,youtube,1,200\n", encoding="utf-8")
    report = build_report(events, metrics)
    assert report["matched_rows"] == 2
    assert {row["variant"] for row in report["rows"]} == {0, 1}


def test_background_manifest_requires_provenance_fields(tmp_path):
    manifest = tmp_path / "backgrounds.json"
    manifest.write_text(json.dumps({"assets": [{"name": "x", "filename": "x.mp4", "url": "https://example.test/x.mp4", "source_page": "https://example.test", "attribution": "Example", "rights_note": "authorized"}]}), encoding="utf-8")
    assert load_asset_manifest(manifest)[0]["name"] == "x"


def test_manifest_records_selected_background(tmp_path):
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    background = tmp_path / "background.mp4"
    background.write_bytes(b"video")
    manifest = save_manifest(fallback_package(Topic("A breakthrough", "AI", (source,))), tmp_path / "short.mp4", tmp_path, background)
    assert json.loads(manifest.read_text(encoding="utf-8"))["background"] == str(background)


def test_background_reel_selection_rotates_stably(tmp_path):
    for name in ("a.mp4", "b.mp4", "c.mp4"):
        (tmp_path / name).write_bytes(name.encode())
    selected = select_backgrounds(tmp_path, "https://example.test/topic")
    assert len(selected) == 3
    assert selected == select_backgrounds(tmp_path, "https://example.test/topic")
    assert {path.name for path in selected} == {"a.mp4", "b.mp4", "c.mp4"}


def test_dockerfile_copies_asset_manifest():
    dockerfile = Path(__file__).parents[1] / "Dockerfile"
    assert "COPY assets ./assets" in dockerfile.read_text(encoding="utf-8")


def test_nas_deploy_script_preserves_remote_environment():
    script = Path(__file__).parents[1] / "scripts" / "deploy-nas.ps1"
    text = script.read_text(encoding="utf-8")
    assert "scp -O" in text
    assert "cp -n .env.example .env" in text
    assert "keys.json" not in text


def test_feed_summary_removes_markup_urls_and_link_aggregator_boilerplate():
    cleaned = _clean_summary('<p>Article URL: <a href="https://example.test">https://example.test</a></p><p>Points: 27</p># Comments: 11')
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


def test_batch_reports_feed_outage_before_claiming_topics_are_seen(monkeypatch):
    monkeypatch.setattr(cli, "discover_topics", lambda limit: [])
    try:
        cli.run_batch(1, force_dry_run=True)
    except RuntimeError as exc:
        assert "RSS feeds may be unavailable" in str(exc)
    else:
        raise AssertionError("empty discovery did not report a feed outage")
