import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cliptool import scout_engine


def test_youtube_without_transcript_uses_distributed_fallback(monkeypatch):
    video = {
        "id": "longvideo",
        "snippet": {"title": "Long upload", "channelTitle": "Channel", "thumbnails": {}},
        "contentDetails": {"duration": "PT1H"},
        "statistics": {"viewCount": "10"},
    }
    cfg = {
        "language_allowlist": ["en"],
        "vod_chunk_seconds": 60,
        "max_candidates_per_source": 25,
        "safety": {"flagged_keywords": []},
    }
    monkeypatch.setattr(scout_engine, "fetch_transcript", lambda *_: None)

    candidates = scout_engine._youtube_video_to_candidates(video, cfg, min_s=8, max_s=90)

    assert len(candidates) == 3
    assert [candidate.start_seconds for candidate in candidates] == [0, 1770, 3540]
    assert all("distributed fixed-interval fallback" in candidate.why_selected for candidate in candidates)
