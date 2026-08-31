from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .models import ScriptPackage, Topic
from .render import _audio_duration, _caption_filter, _font


def _chapter_timestamp(narration: str, marker: str, duration: float | None = None) -> str:
    total_words = max(1, len(narration.split()))
    position = narration.find(f"\n\n{marker}")
    words_before = len(narration[: max(0, position)].split()) if position >= 0 else total_words
    total_duration = duration if duration and duration > 0 else max(30.0, total_words / 2.5)
    seconds = min(max(0, int((words_before / total_words) * total_duration)), 5999)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _chapter_metadata(narration: str, duration: float | None = None) -> str:
    chapters = (
        ("00:00", "Hook"),
        (_chapter_timestamp(narration, "Chapter two: Context:", duration), "Context"),
        (_chapter_timestamp(narration, "Chapter four: Why it matters:", duration), "Technical lesson"),
        (_chapter_timestamp(narration, "Chapter five:", duration), "Limits and takeaway"),
    )
    return "\n".join(f"{timestamp} {label}" for timestamp, label in chapters)


def create_longform_package(topic: Topic) -> ScriptPackage:
    source = topic.sources[0]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source.summary) if part.strip()]
    body_sentences = sentences if len(sentences) <= 40 else [*sentences[:30], *sentences[-10:]]
    body = " ".join(body_sentences)
    hook = f"What actually happened with {source.title}?"
    narration = (
        f"{hook}\n\n"
        f"Chapter one: the claim. Today we are breaking down {source.title}. "
        f"This is a source-backed case study in {topic.category.lower()}, not a claim that one story explains an entire field.\n\n"
        f"Chapter two: Context: what the source says. {body}\n\n"
        "Chapter three: What happened: reconstructing the sequence. The useful way to read this account is to identify the initial condition, "
        "the technical decision or event that followed, and the observable result. The source gives us the reported details; "
        "our job is to connect them carefully without adding facts that are not present.\n\n"
        "Chapter four: Why it matters: the technical lesson. A single incident can still expose a design tradeoff. Ask what assumption failed, "
        "what constraint shaped the outcome, and which control or test would have revealed the problem earlier. Those questions "
        "turn a headline into an engineering lesson while keeping the explanation honest about its limits.\n\n"
        "Chapter five: what we cannot conclude. This source is evidence about the event it describes. It is not, by itself, "
        "a benchmark of every system, proof that every organization works the same way, or a substitute for primary documentation. "
        "Where the source is incomplete, that uncertainty belongs in the story.\n\n"
        "Chapter six: Takeaway: the durable lesson is to separate the reported facts from the interpretation, then test the "
        "interpretation against stronger evidence. For the full context, read the linked source and compare its claims with "
        "primary technical documentation, measurements, or follow-up reporting."
    )
    attribution = f"Reddit attribution: u/{source.author} in r/{source.community}" if source.author else ""
    description = (f"Source: {source.url}\n{attribution}\n\n{_chapter_metadata(narration)}\n\n{narration}").strip()
    return ScriptPackage(
        hook,
        narration,
        source.title[:100],
        description,
        [topic.category, "technology", "technical analysis", "deep dive", "long form"],
        [source.url],
        "longform_explainer",
        topic.category,
    )


def _title_card(package: ScriptPackage, path: Path) -> None:
    image = Image.new("RGB", (1920, 1080), (10, 18, 34))
    draw = ImageDraw.Draw(image)
    font = _font(72, bold=True)
    lines = textwrap.wrap(package.title, width=30)
    draw.multiline_text((120, 350), "\n".join(lines), fill="white", font=font, spacing=18)
    draw.text((125, 820), f"{package.category} | source-backed explainer", fill=(150, 190, 230), font=_font(32))
    image.save(path)


def render_longform_video(
    package: ScriptPackage, output_dir: Path, audio: Path, captions: Path | None, background: Path | None
) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "title-card.png"
    _title_card(package, card)
    output = output_dir / "longform.mp4"
    measured_audio = _audio_duration(audio)
    duration = (
        measured_audio if measured_audio and measured_audio > 0 else max(30.0, len(package.narration.split()) / 2.5)
    )
    package.description = package.description.replace(
        _chapter_metadata(package.narration), _chapter_metadata(package.narration, duration)
    )
    command = ["ffmpeg", "-y"]
    if background and background.exists():
        command += ["-stream_loop", "-1", "-i", str(background)]
        background_input = "[0:v]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,eq=saturation=1.05:contrast=1.04[bg]"
        video = "[bg]"
        next_input = 1
    else:
        command += ["-f", "lavfi", "-i", "color=c=0b1222:s=1920x1080:r=30"]
        background_input = "[0:v]format=yuv420p[bg]"
        video = "[bg]"
        next_input = 1
    command += ["-loop", "1", "-i", str(card), "-i", str(audio)]
    filters = [background_input, f"{video}[{next_input}:v]overlay=0:0:enable='between(t,0,6)'[base]"]
    video_label = "[base]"
    if captions and captions.exists():
        filters.append(f"{video_label}{_caption_filter(captions, margin_v=70)}[captioned]")
        video_label = "[captioned]"
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        video_label,
        "-map",
        "2:a",
        "-t",
        str(duration),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=600)
    return output
