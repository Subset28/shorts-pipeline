"""Turns a full-length video into scored, bounded candidate windows.

Two strategies:
- score_transcript_windows: transcript-driven scoring (YouTube, when a
  transcript is available). Slides [min,max]-second windows, scores
  each on a weighted mix of signals, returns the top non-overlapping
  windows.
- fixed_interval_windows: dumb even chunking, used as the fallback for
  Twitch VODs (rarely captioned). Lower confidence; callers should mark
  it as such.
- distributed_fixed_interval_windows: a deliberately small, spread-out
  fallback set for YouTube videos with no transcript, so one long upload
  does not crowd out the rest of a channel scout.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..transcript import TranscriptSegment

_EXCITEMENT_RE = re.compile(r"[!?]")


@dataclass
class ScoredWindow:
    start_seconds: float
    end_seconds: float
    score: float
    why_selected: str
    transcript_excerpt: str


def _window_step(min_seconds: int) -> float:
    # Slide by half the minimum window so we don't miss short spikes,
    # but don't so over-sample that scoring gets expensive.
    return max(min_seconds / 2, 4)


def score_transcript_windows(
    segments: List[TranscriptSegment],
    *,
    min_seconds: int,
    max_seconds: int,
    title: str,
    keyword_weights: Dict[str, float],
    excluded_terms: Optional[List[str]] = None,
    duration_hint: Optional[float] = None,
    view_count: Optional[int] = None,
    published_recency_days: Optional[float] = None,
    max_windows: int = 10,
    min_gap_seconds: float = 30,
) -> List[ScoredWindow]:
    if not segments:
        return []

    excluded_terms = [t.lower() for t in (excluded_terms or [])]
    total_duration = segments[-1]["start"] + segments[-1]["duration"]
    window_len = min(max_seconds, max(min_seconds, min_seconds))  # start at the min bound
    step = _window_step(min_seconds)

    title_words = {w.lower() for w in re.findall(r"\w+", title) if len(w) > 3}

    candidates: List[ScoredWindow] = []
    t = 0.0
    while t + min_seconds <= total_duration:
        end = min(t + window_len, total_duration)
        window_segments = [s for s in segments if s["start"] >= t and s["start"] < end]
        text = " ".join(s["text"] for s in window_segments)
        text_lower = text.lower()

        if excluded_terms and any(term in text_lower for term in excluded_terms):
            t += step
            continue

        words = re.findall(r"\w+", text_lower)
        word_count = len(words) or 1

        keyword_density = sum(1 for w in words if w in title_words) / word_count
        title_keyword_match = 1.0 if any(w in text_lower for w in title_words) else 0.0
        punctuation_excitement = min(len(_EXCITEMENT_RE.findall(text)) / max(word_count / 20, 1), 1.0)
        # crude "density spike": more words per second than the video average = more happening
        avg_wps = sum(len(re.findall(r"\w+", s["text"])) for s in segments) / max(total_duration, 1)
        this_wps = word_count / max(end - t, 1)
        transcript_density_spike = min(this_wps / max(avg_wps, 0.01) / 2, 1.0)
        short_duration_preference = 1.0 - ((end - t) - min_seconds) / max(max_seconds - min_seconds, 1)
        recency = 1.0 if published_recency_days is not None and published_recency_days < 30 else 0.3
        popularity = min((view_count or 0) / 100000, 1.0)

        score = (
            keyword_weights.get("keyword_density", 1.0) * keyword_density
            + keyword_weights.get("title_keyword_match", 0.5) * title_keyword_match
            + keyword_weights.get("punctuation_excitement", 0.5) * punctuation_excitement
            + keyword_weights.get("transcript_density_spike", 1.0) * transcript_density_spike
            + keyword_weights.get("short_duration_preference", 0.3) * short_duration_preference
            + keyword_weights.get("recency", 0.2) * recency
            + keyword_weights.get("popularity", 0.3) * popularity
        )

        why = (
            f"keyword_density={keyword_density:.2f} title_match={title_keyword_match:.0f} "
            f"excitement={punctuation_excitement:.2f} density_spike={transcript_density_spike:.2f} "
            f"duration_pref={short_duration_preference:.2f} recency={recency:.2f} popularity={popularity:.2f}"
        )

        candidates.append(ScoredWindow(t, end, score, why, text.strip()))
        t += step

    candidates.sort(key=lambda w: w.score, reverse=True)

    selected: List[ScoredWindow] = []
    for c in candidates:
        if any(not (c.end_seconds <= s.start_seconds - min_gap_seconds or c.start_seconds >= s.end_seconds + min_gap_seconds) for s in selected):
            continue
        selected.append(c)
        if len(selected) >= max_windows:
            break

    selected.sort(key=lambda w: w.start_seconds)
    return selected


def fixed_interval_windows(
    total_duration_seconds: float,
    *,
    chunk_seconds: int,
    max_windows: int = 10,
) -> List[ScoredWindow]:
    windows: List[ScoredWindow] = []
    t = 0.0
    while t < total_duration_seconds and len(windows) < max_windows:
        end = min(t + chunk_seconds, total_duration_seconds)
        if end - t < 1:
            break
        windows.append(
            ScoredWindow(
                start_seconds=t,
                end_seconds=end,
                score=0.1,
                why_selected="fixed-interval fallback (low confidence: no transcript/chat signal used)",
                transcript_excerpt="",
            )
        )
        t += chunk_seconds
    return windows


def distributed_fixed_interval_windows(
    total_duration_seconds: float,
    *,
    chunk_seconds: int,
    max_windows: int = 10,
    fallback_window_limit: int = 3,
) -> List[ScoredWindow]:
    """Return a small set of evenly distributed low-confidence windows.

    No transcript provides no evidence that adjacent parts of a long video
    are independently worth clipping.  Capping and spreading fallback
    windows preserves source diversity in channel scouting while still
    giving a user a representative sample of the upload.
    """
    if total_duration_seconds < 1 or chunk_seconds < 1 or max_windows < 1:
        return []

    available_non_overlapping_windows = int(-(-total_duration_seconds // chunk_seconds))
    window_count = min(max_windows, fallback_window_limit, available_non_overlapping_windows)
    if total_duration_seconds <= chunk_seconds or window_count == 1:
        starts = [0.0]
    elif available_non_overlapping_windows == window_count:
        starts = [float(index * chunk_seconds) for index in range(window_count)]
    else:
        last_start = total_duration_seconds - chunk_seconds
        starts = [last_start * index / (window_count - 1) for index in range(window_count)]

    return [
        ScoredWindow(
            start_seconds=start,
            end_seconds=min(start + chunk_seconds, total_duration_seconds),
            score=0.1,
            why_selected="distributed fixed-interval fallback (low confidence: no transcript/chat signal used)",
            transcript_excerpt="",
        )
        for start in starts
    ]
