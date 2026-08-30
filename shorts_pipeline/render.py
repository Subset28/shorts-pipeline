from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScriptPackage


def _estimated_duration(text: str) -> float:
    return max(10.0, min(60.0, len(text.split()) / 2.5))


def _caption_filter(captions: Path) -> str:
    ass_file = captions.with_suffix(".ass") if captions.suffix.lower() == ".srt" else captions
    caption_file = str(ass_file.resolve()).replace("\\", "/").replace(":", r"\:")
    if ass_file.exists():
        return f"ass='{caption_file}'"
    style = "FontName=Arial,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginL=80,MarginR=80,MarginV=430"
    return f"subtitles='{caption_file}':original_size=1080x1920:force_style='{style}'"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _card(package: ScriptPackage, path: Path, transparent: bool = False) -> None:
    image = Image.new("RGBA" if transparent else "RGB", (1080, 1920), (0, 0, 0, 0) if transparent else (12, 20, 38))
    draw = ImageDraw.Draw(image)
    font = _font(40 if transparent else 54)
    if transparent:
        lines = textwrap.wrap(package.hook.upper(), width=30)[:3]
        draw.multiline_text((60, 230), "\n".join(lines), fill="white", font=font, spacing=8, stroke_width=2, stroke_fill=(0, 0, 0, 230))
    else:
        draw.rounded_rectangle((48, 450, 1032, 820), radius=34, fill=(5, 10, 22, 190) if transparent else (5, 10, 22))
        lines = textwrap.wrap(package.hook, width=29)[:4]
        draw.multiline_text((86, 515), "\n".join(lines), fill="white", font=font, spacing=14)
    image.save(path)


def render_video(package: ScriptPackage, output_dir: Path, audio: Path | None = None, captions: Path | None = None, background: Path | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "card.png"
    try:
        _card(package, card, transparent=bool(background and background.exists()))
    except OSError:
        # Windows installations can lack Arial; the video still renders with
        # a plain card rather than silently skipping the artifact.
        Image.new("RGB", (1080, 1920), (12, 20, 38)).save(card)
    output = output_dir / "short.mp4"
    duration = _estimated_duration(package.narration)
    if background and background.exists():
        command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(background), "-loop", "1", "-i", str(card)]
        audio_index = 2
        if audio:
            command += ["-i", str(audio)]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        video_filter = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=saturation=1.15:contrast=1.08:brightness=-0.04[bg];[bg][1:v]overlay=0:0"
        if captions and captions.exists():
            video_filter += "," + _caption_filter(captions)
        command += ["-filter_complex", video_filter + "[v]", "-map", "[v]", "-map", f"{audio_index}:a", "-t", str(duration), "-r", "30", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(output)]
    else:
        command = ["ffmpeg", "-y", "-loop", "1", "-i", str(card)]
        if audio:
            command += ["-i", str(audio), "-shortest"]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(duration)]
        video_filter = "scale=1080:1920"
        if captions and captions.exists():
            video_filter += "," + _caption_filter(captions)
        command += ["-vf", video_filter, "-r", "30", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output
