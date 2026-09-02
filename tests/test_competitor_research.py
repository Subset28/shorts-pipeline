from datetime import datetime, timezone

import pytest

from shorts_pipeline.competitor_research import (
    YouTubeDataApiProvider,
    build_research_packet,
    channel_outlier,
    compute_velocity,
    load_metadata_fixture,
)


def _video(channel: str, number: int, *, hook: str = "consequence", views: int = 1000) -> dict:
    return {
        "channel_id": channel,
        "video_id": f"{channel}-{number}",
        "published_at": "2026-08-31T00:00:00Z",
        "views": views,
        "likes": 20,
        "comments": 5,
        "duration_seconds": 28,
        "hook_archetype": hook,
        "first_visual": "system diagram",
        "context_seconds": 4,
        "escalation_seconds": 11,
        "mechanism_seconds": 18,
        "payoff_seconds": 25,
        "shot_count": 8,
        "caption_words_per_burst": 4,
        "ending_type": "loop",
    }


def test_velocity_uses_six_hour_floor():
    assert compute_velocity(1200, 2) == 200
    assert compute_velocity(1200, 12) == 100


def test_outlier_uses_nearest_age_comparables_and_safe_zero_baseline():
    assert channel_outlier(3000, [1000, 1100, 900]) == pytest.approx(3.0)
    assert channel_outlier(3000, [0, 0]) == 0.0


def test_packet_keeps_only_patterns_seen_in_three_independent_channels():
    records = []
    for channel in range(10):
        hook = "consequence" if channel < 3 else ("question" if channel < 5 else "reversal")
        records.append(_video(f"c{channel}", 1, hook=hook, views=5000 if channel < 3 else 100))
    packet = build_research_packet(records, datetime(2026, 9, 1, tzinfo=timezone.utc))
    patterns = {item["hook_archetype"]: item for item in packet["patterns"]}
    assert "consequence" in patterns
    assert patterns["consequence"]["independent_channels"] == 3
    assert "question" not in patterns
    assert packet["outliers"][0]["video_id"] == "c0-1"


def test_fixture_loader_rejects_private_or_media_fields(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text('[{"channel_id":"c1","video_id":"v1","token":"secret"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="sensitive field"):
        load_metadata_fixture(path)


def test_packet_is_deterministic_and_has_no_production_media_paths():
    records = [_video(f"c{channel}", 1) for channel in range(10)]
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    first = build_research_packet(records, now)
    second = build_research_packet(list(reversed(records)), now)
    assert first == second
    assert all("media_path" not in item for item in first["outliers"])


def test_youtube_provider_reads_public_metadata_without_titles_or_media():
    class Request:
        def __init__(self, value):
            self.value = value

        def execute(self):
            return self.value

    class Service:
        def channels(self):
            return type(
                "Channels",
                (),
                {
                    "list": lambda self, **kwargs: Request(
                        {"items": [{"id": "c1", "contentDetails": {"relatedPlaylists": {"uploads": "p1"}}}]}
                    )
                },
            )()

        def playlistItems(self):
            return type(
                "Items",
                (),
                {"list": lambda self, **kwargs: Request({"items": [{"contentDetails": {"videoId": "v1"}}]})},
            )()

        def videos(self):
            return type(
                "Videos",
                (),
                {
                    "list": lambda self, **kwargs: Request(
                        {
                            "items": [
                                {
                                    "id": "v1",
                                    "snippet": {"publishedAt": "2026-08-31T00:00:00Z", "title": "omit"},
                                    "statistics": {"viewCount": "10"},
                                    "contentDetails": {"duration": "PT1M2S"},
                                }
                            ]
                        }
                    )
                },
            )()

    row = YouTubeDataApiProvider(Service()).videos_for_channels(["c1"])[0]
    assert row["duration_seconds"] == 62
    assert "title" not in row
