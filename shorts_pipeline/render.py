from __future__ import annotations

import shutil
import subprocess
import textwrap
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScriptPackage


def _estimated_duration(text: str) -> float:
    return max(10.0, min(60.0, len(text.split()) / 2.5))


def _caption_filter(captions: Path, margin_v: int = 430) -> str:
    ass_file = captions.with_suffix(".ass") if captions.suffix.lower() == ".srt" else captions
    caption_file = str(ass_file.resolve()).replace("\\", "/").replace(":", r"\:")
    if ass_file.exists():
        return f"subtitles='{caption_file}':force_style='MarginV={margin_v}'"
    style = "FontName=Arial,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginL=80,MarginR=80,MarginV=430"
    return f"subtitles='{caption_file}':original_size=1080x1920:force_style='{style}'"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _card(package: ScriptPackage, path: Path, transparent: bool = False, show_hook: bool = True) -> None:
    image = Image.new("RGBA" if transparent else "RGB", (1080, 1920), (0, 0, 0, 0) if transparent else (12, 20, 38))
    draw = ImageDraw.Draw(image)
    font = _font(40 if transparent else 54)
    if transparent and show_hook:
        lines = textwrap.wrap(package.hook.upper(), width=30)[:3]
        draw.multiline_text((60, 230), "\n".join(lines), fill="white", font=font, spacing=8, stroke_width=2, stroke_fill=(0, 0, 0, 230))
    elif not transparent:
        draw.rounded_rectangle((48, 450, 1032, 820), radius=34, fill=(5, 10, 22, 190) if transparent else (5, 10, 22))
        lines = textwrap.wrap(package.hook, width=29)[:4]
        draw.multiline_text((86, 515), "\n".join(lines), fill="white", font=font, spacing=14)
    image.save(path)


def _reddit_post_card(package: ScriptPackage, path: Path) -> None:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    body_font = _font(34)
    username_font = _font(27)
    small = _font(24)
    attribution = re.search(r"Reddit attribution: u/([^ ]+) in r/([^\n]+)", package.description)
    username = attribution.group(1) if attribution else "story_author"
    community = attribution.group(2).strip() if attribution else "redditstories"
    top = 300
    bottom = 850
    draw.rounded_rectangle((58, top, 1022, bottom), radius=24, fill=(250, 250, 250, 252), outline=(215, 215, 215, 255), width=3)

    # Compact Reddit-style header with a recognizable orange avatar and metadata.
    draw.ellipse((94, top + 38, 158, top + 102), fill=(255, 69, 0, 255))
    draw.ellipse((111, top + 58, 117, top + 64), fill=(255, 255, 255, 255))
    draw.ellipse((133, top + 58, 139, top + 64), fill=(255, 255, 255, 255))
    draw.arc((112, top + 54, 137, top + 80), 15, 165, fill=(255, 255, 255, 255), width=3)
    draw.text((180, top + 37), f"u/{username}", fill=(35, 35, 35), font=username_font)
    draw.ellipse((180 + int(draw.textlength(f"u/{username}", font=username_font)) + 14, top + 43, 180 + int(draw.textlength(f"u/{username}", font=username_font)) + 34, top + 63), fill=(38, 132, 255, 255))
    draw.text((180, top + 73), f"r/{community}  ·  6h", fill=(120, 120, 120), font=small)
    badge_x = 180
    for color in ((255, 69, 0, 255), (255, 190, 0, 255), (76, 175, 80, 255), (145, 95, 220, 255)):
        draw.ellipse((badge_x, top + 108, badge_x + 18, top + 126), fill=color)
        badge_x += 27
    draw.text((940, top + 48), "···", fill=(100, 100, 100), font=username_font)

    # The narration contains the complete story summary. The description is
    # deliberately shorter metadata, so using it here can leave the card
    # with only a headline and a large empty body area.
    story_match = re.search(r"Here's what happened:\s*(.*?)(?:\s+The useful part|\Z)", package.narration, re.S)
    story = story_match.group(1).strip() if story_match else package.title
    story = re.sub(r"^\[FICTIONAL REVIEW DEMO\]\s*", "", story)
    lines = textwrap.wrap(story, width=44)[:5]
    draw.multiline_text((94, top + 150), "\n".join(lines), fill=(20, 20, 20), font=body_font, spacing=10)
    draw.line((94, bottom - 90, 986, bottom - 90), fill=(225, 225, 225), width=2)
    draw.text((112, bottom - 66), "♡  Like", fill=(100, 100, 100), font=small)
    draw.text((330, bottom - 66), "◯  Comment", fill=(100, 100, 100), font=small)
    draw.text((800, bottom - 66), "Share", fill=(100, 100, 100), font=small)
    image.save(path)


def render_video(package: ScriptPackage, output_dir: Path, audio: Path | None = None, captions: Path | None = None, background: Path | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "card.png"
    try:
        _card(package, card, transparent=bool(background and background.exists()), show_hook=package.format_name != "reddit_story")
    except OSError:
        # Windows installations can lack Arial; the video still renders with
        # a plain card rather than silently skipping the artifact.
        Image.new("RGB", (1080, 1920), (12, 20, 38)).save(card)
    output = output_dir / "short.mp4"
    duration = _estimated_duration(package.narration)
    if background and background.exists():
        command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(background), "-loop", "1", "-i", str(card)]
        audio_index = 2
        if package.format_name == "reddit_story":
            reddit_card = output_dir / "reddit-post-card.png"
            _reddit_post_card(package, reddit_card)
            command += ["-loop", "1", "-i", str(reddit_card)]
            audio_index = 3
        if audio:
            command += ["-i", str(audio)]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        video_filter = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=saturation=1.15:contrast=1.08:brightness=-0.04[bg];[bg][1:v]overlay=0:0"
        if package.format_name == "reddit_story":
            video_filter = video_filter.replace("[bg][1:v]overlay=0:0", "[bg][1:v]overlay=0:0[base];[base][2:v]overlay=0:0:enable='between(t,0,4)'")
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
