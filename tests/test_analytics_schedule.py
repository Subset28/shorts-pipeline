import json
from datetime import datetime, timedelta, timezone

from shorts_pipeline.analytics_schedule import due_videos, load_publications, week_videos
from shorts_pipeline.youtube_analytics import write_weekly_report


def _event(path, video_id, timestamp):
    path.write_text(
        json.dumps(
            {
                "event": "youtube_published",
                "platform_id": video_id,
                "source_url": f"https://example.test/{video_id}",
                "timestamp": timestamp,
                "category": "AI",
                "format_name": "fact_explainer",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_due_videos_start_at_24_hours_and_repeat_daily(tmp_path):
    now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
    events = tmp_path / "events.jsonl"
    _event(events, "abc", (now - timedelta(hours=48)).isoformat())
    assert [item["video_id"] for item in due_videos(events, tmp_path / "snapshots.json", now)] == ["abc"]
    (tmp_path / "snapshots.json").write_text(
        json.dumps({"abc": [{"collected_at": (now - timedelta(hours=23)).isoformat()}]}), encoding="utf-8"
    )
    assert due_videos(events, tmp_path / "snapshots.json", now) == []


def test_due_videos_ignores_non_list_snapshot_values(tmp_path):
    now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
    events = tmp_path / "events.jsonl"
    _event(events, "abc", (now - timedelta(hours=48)).isoformat())
    snapshots = tmp_path / "snapshots.json"
    snapshots.write_text(json.dumps({"abc": None}), encoding="utf-8")

    assert [item["video_id"] for item in due_videos(events, snapshots, now)] == ["abc"]


def test_week_videos_returns_only_current_monday_to_sunday_uploads(tmp_path):
    now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "youtube_published",
                        "platform_id": "this-week",
                        "timestamp": (now - timedelta(days=1)).isoformat(),
                    }
                ),
                json.dumps(
                    {
                        "event": "youtube_published",
                        "platform_id": "last-week",
                        "timestamp": (now - timedelta(days=8)).isoformat(),
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert [item["video_id"] for item in week_videos(events, now)] == ["this-week"]


def test_weekly_report_ignores_non_list_snapshot_values(tmp_path):
    now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
    events = tmp_path / "events.jsonl"
    _event(events, "abc", (now - timedelta(days=1)).isoformat())
    snapshots = tmp_path / "snapshots.json"
    snapshots.write_text(json.dumps({"abc": None}), encoding="utf-8")
    output = tmp_path / "weekly.json"

    write_weekly_report(events, snapshots, output, now)

    assert json.loads(output.read_text(encoding="utf-8"))["snapshots"] == []


def test_publications_ignore_non_youtube_and_duplicate_events(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {"event": "tiktok_published", "platform_id": "nope", "timestamp": "2026-08-30T00:00:00+00:00"}
                ),
                json.dumps(
                    {"event": "youtube_published", "platform_id": "abc", "timestamp": "2026-08-30T00:00:00+00:00"}
                ),
                json.dumps(
                    {"event": "youtube_published", "platform_id": "abc", "timestamp": "2026-08-30T00:01:00+00:00"}
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert [item["video_id"] for item in load_publications(events)] == ["abc"]
