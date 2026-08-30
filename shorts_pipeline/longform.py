from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .models import ScriptPackage, Topic
from .render import _caption_filter, _font


def create_longform_package(topic: Topic) -> ScriptPackage:
    source = topic.sources[0]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source.summary) if part.strip()]
    body = " ".join(sentences)
    narration = (
        f"Today we are breaking down {source.title}. "
        f"This is not just a headline. It is a useful case study in {topic.category.lower()}.\n\n"
        f"Context: The source reports: {body}\n\n"
        f"What happened: The important sequence is the concrete chain of events above, which we can examine without treating one post as universal proof.\n\n"
        f"Why it matters: In practical terms, this shows how technical decisions create consequences outside the code or equipment itself. "
        f"The strongest lesson is to separate what the source directly reports from what we can reasonably infer.\n\n"
        f"Takeaway: The story is useful because it gives us a concrete example to examine, not because one post proves a universal rule. "
        f"For the full context, read the linked source and compare the claims with primary evidence."
    )
    description = f"{narration}\n\nSource: {source.url}\nReddit attribution: u/{source.author} in r/{source.community}"
    return ScriptPackage(
        source.title[:100],
        narration,
        source.title[:100],
        description,
        [topic.category, "technology", "explainer", "long form"],
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
    duration = max(30.0, len(package.narration.split()) / 2.5)
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
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output
