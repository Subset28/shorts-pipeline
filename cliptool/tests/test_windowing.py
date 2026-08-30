import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cliptool.scout.windowing import (
    distributed_fixed_interval_windows,
    fixed_interval_windows,
    score_transcript_windows,
)


def make_segments():
    # 120s video, exciting keyword-dense burst around 40-70s
    segments = []
    t = 0.0
    while t < 120:
        text = "just talking normally here"
        if 40 <= t < 70:
            text = "amazing incredible clutch play! insane! wow!"
        segments.append({"text": text, "start": t, "duration": 5})
        t += 5
    return segments


def test_score_transcript_windows_finds_the_exciting_segment():
    segments = make_segments()
    windows = score_transcript_windows(
        segments,
        min_seconds=10,
        max_seconds=30,
        title="Amazing Incredible Clutch Play",
        keyword_weights={
            "keyword_density": 1.0,
            "title_keyword_match": 0.5,
            "punctuation_excitement": 0.5,
            "transcript_density_spike": 1.0,
            "short_duration_preference": 0.3,
            "recency": 0.2,
            "popularity": 0.3,
        },
        max_windows=3,
        min_gap_seconds=5,
    )
    assert len(windows) > 0
    top = windows[0] if len(windows) == 1 else max(windows, key=lambda w: w.score)
    assert 30 <= top.start_seconds <= 75


def test_score_transcript_windows_respects_bounds():
    segments = make_segments()
    windows = score_transcript_windows(
        segments,
        min_seconds=10,
        max_seconds=30,
        title="test",
        keyword_weights={},
        max_windows=5,
        min_gap_seconds=5,
    )
    for w in windows:
        duration = w.end_seconds - w.start_seconds
        assert 10 <= duration <= 30 + 0.01


def test_score_transcript_windows_excludes_terms():
    segments = make_segments()
    windows = score_transcript_windows(
        segments,
        min_seconds=10,
        max_seconds=30,
        title="test",
        keyword_weights={},
        excluded_terms=["amazing"],
        max_windows=5,
        min_gap_seconds=5,
    )
    for w in windows:
        assert "amazing" not in w.transcript_excerpt.lower()


def test_fixed_interval_windows_covers_full_duration():
    windows = fixed_interval_windows(100, chunk_seconds=30, max_windows=10)
    assert len(windows) == 4
    assert windows[0].start_seconds == 0
    assert windows[-1].end_seconds == 100
    for w in windows:
        assert w.why_selected.startswith("fixed-interval fallback")


def test_fixed_interval_windows_respects_max_windows():
    windows = fixed_interval_windows(1000, chunk_seconds=10, max_windows=5)
    assert len(windows) == 5


def test_distributed_fixed_interval_windows_caps_and_spreads_long_video_fallbacks():
    windows = distributed_fixed_interval_windows(3600, chunk_seconds=60, max_windows=25)

    assert len(windows) == 3
    assert [window.start_seconds for window in windows] == [0, 1770, 3540]
    assert all(window.end_seconds - window.start_seconds == 60 for window in windows)
    assert all("distributed" in window.why_selected for window in windows)


def test_distributed_fixed_interval_windows_keeps_short_videos_whole():
    windows = distributed_fixed_interval_windows(45, chunk_seconds=60, max_windows=25)

    assert len(windows) == 1
    assert windows[0].start_seconds == 0
    assert windows[0].end_seconds == 45


def test_distributed_fixed_interval_windows_never_overlaps_short_fallbacks():
    windows = distributed_fixed_interval_windows(61, chunk_seconds=60, max_windows=25)

    assert [(window.start_seconds, window.end_seconds) for window in windows] == [(0, 60), (60, 61)]


def test_no_segments_returns_empty():
    assert score_transcript_windows([], min_seconds=8, max_seconds=90, title="x", keyword_weights={}) == []
