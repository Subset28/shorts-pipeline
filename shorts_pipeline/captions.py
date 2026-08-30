from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _timestamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fallback_segments(text: str, duration: float) -> list[tuple[float, float, str]]:
    words = _clean(text).split()
    if not words:
        return []
    chunks = [words[i : i + 6] for i in range(0, len(words), 6)]
    step = max(duration, 1.0) / len(chunks)
    return [(i * step, min(duration, (i + 1) * step), " ".join(chunk)) for i, chunk in enumerate(chunks)]


def _write_srt(segments: list[tuple[float, float, str]], output: Path) -> Path | None:
    usable = [(start, end, _clean(text)) for start, end, text in segments if _clean(text)]
    if not usable:
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    body = []
    for index, (start, end, text) in enumerate(usable, 1):
        body.append(f"{index}\n{_timestamp(start)} --> {_timestamp(max(end, start + 0.2))}\n{text}\n")
    output.write_text("\n".join(body), encoding="utf-8-sig")
    return output


def _audio_duration(audio: Path | None) -> float:
    if not audio or not audio.exists():
        return 10.0
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
            check=True, capture_output=True, text=True, timeout=20,
        )
        return max(float(result.stdout.strip()), 1.0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 10.0


def create_captions(text: str, audio: Path | None, output: Path, model_name: str = "base") -> Path | None:
    """Create SRT with local faster-whisper when available, otherwise time text."""
    if audio and audio.exists():
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(audio), word_timestamps=True, vad_filter=True)
            whisper_segments = []
            for segment in segments:
                words = getattr(segment, "words", None) or []
                caption_text = " ".join(word.word.strip() for word in words).strip() or segment.text
                whisper_segments.append((float(segment.start), float(segment.end), caption_text))
            result = _write_srt(whisper_segments, output)
            if result:
                return result
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            print(f"Whisper unavailable; using timed captions: {exc}")
    return _write_srt(_fallback_segments(text, _audio_duration(audio)), output)
