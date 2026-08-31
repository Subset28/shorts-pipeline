from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

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


def _chapter_metadata(
    narration: str, duration: float | None = None, chapter_markers: tuple[str, ...] | None = None
) -> str:
    markers = chapter_markers or ("Context", "Why it matters", "Limits")
    chapters = (
        ("00:00", "Hook"),
        (_chapter_timestamp(narration, f"Chapter two: {markers[0]}:", duration), markers[0]),
        (_chapter_timestamp(narration, f"Chapter four: {markers[1]}:", duration), "Technical lesson"),
        (_chapter_timestamp(narration, f"Chapter five: {markers[2]}:", duration), "Limits and takeaway"),
    )
    return "\n".join(f"{timestamp} {label}" for timestamp, label in chapters)


def _narration_chapter_markers(narration: str) -> tuple[str, str, str]:
    defaults = ("Context", "Why it matters", "Limits")
    markers = []
    for chapter in (2, 4, 5):
        match = re.search(rf"Chapter {chapter}: ([^:]+):", narration)
        markers.append(match.group(1).strip() if match else defaults[len(markers)])
    return tuple(markers)  # type: ignore[return-value]


def _longform_context(topic: Topic, brief: dict[str, Any] | None) -> tuple[str, tuple[str, ...], dict[str, Any] | None]:
    if brief is None:
        return (
            f"What actually happened with {topic.sources[0].title}?",
            ("Context", "What happened", "Why it matters", "Limits", "Takeaway"),
            None,
        )
    source = topic.sources[0]
    if brief.get("privacy_status") != "private":
        raise ValueError("long-form editorial brief must be private")
    brief_source = brief.get("source")
    bridge = brief.get("longform_bridge")
    metadata = brief.get("metadata")
    if not isinstance(brief_source, dict) or brief_source.get("url") != source.url:
        raise ValueError("long-form editorial brief source URL does not match topic")
    if not isinstance(bridge, dict) or not isinstance(metadata, dict):
        raise ValueError("long-form editorial brief requires bridge and metadata objects")
    question = bridge.get("question")
    chapters = bridge.get("chapters")
    if not isinstance(question, str) or not question.strip() or not isinstance(chapters, list) or len(chapters) < 5:
        raise ValueError("long-form editorial brief bridge is incomplete")
    clean_chapters = tuple(str(label).strip()[:80] for label in chapters[:5])
    if any(not label for label in clean_chapters):
        raise ValueError("long-form editorial brief chapters are incomplete")
    title = metadata.get("title")
    description = metadata.get("description")
    tags = metadata.get("tags")
    if not all(isinstance(value, str) and value.strip() for value in (title, description)) or not isinstance(
        tags, list
    ):
        raise ValueError("long-form editorial brief metadata is incomplete")
    if source.url not in description:
        raise ValueError("long-form editorial brief metadata is not source-linked")
    return (
        question.strip(),
        clean_chapters,
        {"title": title.strip()[:100], "description": description.strip(), "tags": tags},
    )


def create_longform_package(topic: Topic, editorial_brief: dict[str, Any] | None = None) -> ScriptPackage:
    source = topic.sources[0]
    question, bridge_chapters, metadata = _longform_context(topic, editorial_brief)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source.summary) if part.strip()]
    body_sentences = sentences if len(sentences) <= 40 else [*sentences[:30], *sentences[-10:]]
    body = " ".join(body_sentences)
    hook = question
    context, happened, matters, limits, takeaway = bridge_chapters
    narration = (
        f"{hook}\n\n"
        f"Chapter one: the claim. Today we are breaking down {source.title}. "
        f"This is a source-backed case study in {topic.category.lower()}, not a claim that one story explains an entire field.\n\n"
        f"Chapter two: {context}: what the source says. {body}\n\n"
        f"Chapter three: {happened}: reconstructing the sequence. The useful way to read this account is to identify the initial condition, "
        "the technical decision or event that followed, and the observable result. The source gives us the reported details; "
        "our job is to connect them carefully without adding facts that are not present.\n\n"
        f"Chapter four: {matters}: the technical lesson. A single incident can still expose a design tradeoff. Ask what assumption failed, "
        "what constraint shaped the outcome, and which control or test would have revealed the problem earlier. Those questions "
        "turn a headline into an engineering lesson while keeping the explanation honest about its limits.\n\n"
        f"Chapter five: {limits}: what we cannot conclude. This source is evidence about the event it describes. It is not, by itself, "
        "a benchmark of every system, proof that every organization works the same way, or a substitute for primary documentation. "
        "Where the source is incomplete, that uncertainty belongs in the story.\n\n"
        f"Chapter six: {takeaway}: the durable lesson is to separate the reported facts from the interpretation, then test the "
        "interpretation against stronger evidence. For the full context, read the linked source and compare its claims with "
        "primary technical documentation, measurements, or follow-up reporting."
    )
    attribution = f"Reddit attribution: u/{source.author} in r/{source.community}" if source.author else ""
    chapter_markers = (context, matters, limits)
    base_description = metadata["description"] if metadata else ""
    description = (
        f"{base_description}\n\nSource: {source.url}\n{attribution}\n\n{_chapter_metadata(narration, chapter_markers=chapter_markers)}\n\n{narration}"
    ).strip()
    tags = (
        metadata["tags"] if metadata else [topic.category, "technology", "technical analysis", "deep dive", "long form"]
    )
    clean_tags = [str(tag).strip()[:30] for tag in tags if str(tag).strip()][:12]
    return ScriptPackage(
        hook,
        narration,
        metadata["title"] if metadata else source.title[:100],
        description,
        clean_tags,
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


def _technical_card(package: ScriptPackage, path: Path) -> None:
    image = Image.new("RGBA", (760, 500), (12, 24, 44, 238))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 752, 492), radius=24, outline=(100, 190, 255, 220), width=3)
    draw.text((32, 28), f"{package.category} | technical map", fill=(175, 220, 255), font=_font(28, bold=True))
    labels = ["Source", "Decision", "Result", "Lesson"]
    x_positions = (36, 214, 392, 570)
    for index, label in enumerate(labels):
        left = x_positions[index]
        draw.rounded_rectangle((left, 190, left + 150, 290), radius=14, fill=(28, 66, 100, 240))
        draw.text((left + 18, 224), label, fill="white", font=_font(22, bold=True))
        if index < len(labels) - 1:
            draw.line((left + 150, 240, x_positions[index + 1] - 12, 240), fill=(105, 210, 255), width=5)
            draw.polygon(
                (
                    (x_positions[index + 1] - 12, 240),
                    (x_positions[index + 1] - 28, 230),
                    (x_positions[index + 1] - 28, 250),
                ),
                fill=(105, 210, 255),
            )
    draw.multiline_text(
        (32, 350),
        "Separate reported facts from\ninterpretation, then test the lesson.",
        fill=(225, 238, 250),
        font=_font(25),
        spacing=8,
    )
    image.save(path)


def render_longform_video(
    package: ScriptPackage, output_dir: Path, audio: Path, captions: Path | None, background: Path | None
) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "title-card.png"
    technical_card = output_dir / "technical-map.png"
    _title_card(package, card)
    _technical_card(package, technical_card)
    output = output_dir / "longform.mp4"
    measured_audio = _audio_duration(audio)
    duration = (
        measured_audio if measured_audio and measured_audio > 0 else max(30.0, len(package.narration.split()) / 2.5)
    )
    chapter_markers = _narration_chapter_markers(package.narration)
    package.description = package.description.replace(
        _chapter_metadata(package.narration, chapter_markers=chapter_markers),
        _chapter_metadata(package.narration, duration, chapter_markers),
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
    command += ["-loop", "1", "-i", str(card), "-loop", "1", "-i", str(technical_card), "-i", str(audio)]
    filters = [
        background_input,
        f"{video}[{next_input}:v]overlay=0:0:enable='between(t,0,6)'[base]",
        "[base][2:v]overlay=1080:520:enable='gte(t,6)'[mapped]",
    ]
    video_label = "[mapped]"
    if captions and captions.exists():
        filters.append(f"{video_label}{_caption_filter(captions, margin_v=70)}[captioned]")
        video_label = "[captioned]"
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        video_label,
        "-map",
        "3:a",
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
