from shorts_pipeline.models import Source, Topic
from shorts_pipeline.history import load_publish_state, save_publish_state
from shorts_pipeline.captions import create_captions
from shorts_pipeline.telemetry import record_event
import json
from shorts_pipeline.publish import metadata
from shorts_pipeline.seo import fallback_package, normalize_package
from shorts_pipeline.media import select_background


def test_fallback_package_preserves_source_url():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert source.url in package.description
    assert package.sources == [source.url]


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
    assert set(data) == {"title", "description", "tags", "sources", "format_name", "category"}
    assert data["category"] == "AI"


def test_publish_state_resumes_each_platform_without_overwriting(tmp_path):
    path = tmp_path / "publish_state.json"
    save_publish_state(path, "https://example.test/source", youtube_id="yt123")
    save_publish_state(path, "https://example.test/source", tiktok_id="tt456")
    assert load_publish_state(path)["https://example.test/source"] == {"tiktok_id": "tt456", "youtube_id": "yt123"}


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
