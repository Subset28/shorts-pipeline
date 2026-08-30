# YouTube fallback diversity — TDD evidence

Source: journeys derived during this TDD run.

User journey: when a YouTube upload has no transcript, a scout user receives a
small, representative set of candidate timestamps instead of many adjacent,
low-confidence windows from that one upload.

| Guarantee | Test | Result |
| --- | --- | --- |
| Long uploads receive at most three evenly spread fallback windows. | `tests/test_windowing.py::test_distributed_fixed_interval_windows_caps_and_spreads_long_video_fallbacks` | PASS |
| Short uploads are represented whole and fallback windows never overlap. | `tests/test_windowing.py::test_distributed_fixed_interval_windows_keeps_short_videos_whole`, `::test_distributed_fixed_interval_windows_never_overlaps_short_fallbacks` | PASS |
| The YouTube no-transcript path uses the distributed fallback. | `tests/test_scout_engine.py::test_youtube_without_transcript_uses_distributed_fallback` | PASS |

RED evidence: `.venv/bin/python -m pytest -q tests/test_windowing.py` failed
with `ImportError` before the fallback selector existed; the short-upload
regression later failed with overlapping windows before its fix.

GREEN evidence: `.venv/bin/python -m pytest -q` completed with `16 passed`.
Coverage was not available because this repository does not declare or install
the `pytest-cov` plugin; `pytest --cov` is not a recognized command here.
