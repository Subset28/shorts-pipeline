from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScriptPackage


def _card(package: ScriptPackage, path: Path) -> None:
    image = Image.new("RGB", (1080, 1920), (12, 20, 38))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 58)
    small = ImageFont.truetype("arial.ttf", 32)
    draw.text((80, 170), "SIGNAL LAB", fill=(92, 220, 180), font=small)
    lines = textwrap.wrap(package.hook, width=25)
    draw.multiline_text((80, 520), "\n".join(lines), fill="white", font=font, spacing=18)
    draw.text((80, 1730), "Source-backed explainer", fill=(160, 174, 192), font=small)
    image.save(path)


def render_video(package: ScriptPackage, output_dir: Path, audio: Path | None = None, captions: Path | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "card.png"
    try:
        _card(package, card)
    except OSError:
        # Windows installations can lack Arial; the video still renders with
        # a plain card rather than silently skipping the artifact.
        Image.new("RGB", (1080, 1920), (12, 20, 38)).save(card)
    output = output_dir / "short.mp4"
    command = ["ffmpeg", "-y", "-loop", "1", "-i", str(card)]
    if audio:
        command += ["-i", str(audio), "-shortest"]
    else:
        command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "10"]
    video_filter = "scale=1080:1920"
    if captions and captions.exists():
        caption_file = str(captions.resolve()).replace("\\", "/").replace(":", r"\:")
        video_filter += f",subtitles='{caption_file}'"
    command += ["-vf", video_filter, "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output
