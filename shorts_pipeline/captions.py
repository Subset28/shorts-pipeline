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


def _ass_timestamp(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


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


def _write_ass(segments: list[tuple[float, float, str]], output: Path) -> Path | None:
    usable = [(start, end, _clean(text)) for start, end, text in segments if _clean(text)]
    if not usable:
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H0000D7FF,&H0000D7FF,&H00101010,&H99000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, text in usable:
        wrapped = "\\N".join(" ".join(text.split()[i : i + 4]) for i in range(0, len(text.split()), 4))
        wrapped = wrapped.upper()
        events.append(f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(max(end, start + 0.2))},Default,,0,0,0,,{wrapped}")
    output.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return output


def write_speaker_ass(segments: list[dict], output: Path) -> Path | None:
    """Write speaker-colored ASS events from diarization/WhisperX segments.

    Each item needs ``start``, ``end``, ``text`` and may include ``speaker``.
    This is intentionally separate from the one-narrator path: colors indicate
    diarized speaker identity, never guessed sentence alternation.
    """
    usable = [(float(item["start"]), float(item["end"]), _clean(str(item["text"])), str(item.get("speaker", "SPEAKER_00"))) for item in segments if _clean(str(item.get("text", "")))]
    if not usable:
        return None
    speakers = {speaker: index % 4 for index, speaker in enumerate(dict.fromkeys(item[3] for item in usable))}
    colors = ["&H0000D7FF", "&H0000FF80", "&H00FFFF00", "&H00FF80FF"]
    styles = "\n".join(
        f"Style: Speaker{index},Arial,48,{colors[index]},&H00FFFFFF,&H00101010,&H99000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,430,1"
        for index in range(4)
    )
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, text, speaker in usable:
        wrapped = "\\N".join(" ".join(text.upper().split()[i : i + 4]) for i in range(0, len(text.split()), 4))
        events.append(f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(max(end, start + 0.2))},Speaker{speakers[speaker]},,0,0,0,,{wrapped}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
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


def _estimated_duration(text: str) -> float:
    return max(10.0, min(60.0, len(_clean(text).split()) / 2.5))


def _write_caption_files(segments: list[tuple[float, float, str]], output: Path) -> Path | None:
    result = _write_srt(segments, output)
    if result:
        _write_ass(segments, output.with_suffix(".ass"))
    return result


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
            result = _write_caption_files(whisper_segments, output)
            if result:
                return result
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            print(f"Whisper unavailable; using timed captions: {exc}")
    duration = _audio_duration(audio) if audio else _estimated_duration(text)
    return _write_caption_files(_fallback_segments(text, duration), output)
