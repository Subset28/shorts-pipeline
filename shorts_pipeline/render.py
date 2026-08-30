from __future__ import annotations

import shutil
import subprocess
import textwrap
import re
import os
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


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf") if bold else ("arial.ttf", "C:/Windows/Fonts/arial.ttf")
    names += ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",)
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _asset(path: Path, size: tuple[int, int]) -> Image.Image | None:
    """Load an optional transparent card asset without making it mandatory."""
    if not path.exists():
        return None
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return image
    except (OSError, ValueError):
        return None


def _paste_circle(base: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    image = image.resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, image.width - 1, image.height - 1), fill=255)
    base.paste(image, (box[0], box[1]), mask)


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
    body_font = _font(40, bold=True)
    username_font = _font(28, bold=True)
    small = _font(22)
    asset_dir = Path(os.getenv("REDDIT_ASSETS_DIR", "assets/reddit"))
    attribution = re.search(r"Reddit attribution: u/([^ ]+) in r/([^\n]+)", package.description)
    username = attribution.group(1) if attribution else "story_author"
    community = attribution.group(2).strip() if attribution else "redditstories"
    # Match the reference treatment: a compact post floating over the game,
    # rather than a full-width panel that dominates the opening frame.
    left, right = 35, 1045
    top = 650
    story = package.title.strip()
    if len(story.split()) < 12:
        story_match = re.search(r"Here's what happened:\s*(.*?)(?:\s+The useful part|\Z)", package.narration, re.S)
        narrated_story = story_match.group(1).strip() if story_match else ""
        # Keep the card punchy and avoid ending on a clipped clause.
        first_sentence = re.split(r"(?<=[.!?])\s+", narrated_story, maxsplit=1)[0]
        story = first_sentence or story
    story = re.sub(r"^\[FICTIONAL REVIEW DEMO\]\s*", "", story)
    lines = textwrap.wrap(story, width=45)[:6]
    bottom = max(top + 490, top + 150 + (len(lines) * 48) + 90)
    draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=(250, 250, 250, 252), outline=(215, 215, 215, 255), width=3)

    # Compact Reddit-style header with a recognizable orange avatar and metadata.
    avatar = _asset(asset_dir / "avatar.png", (58, 58))
    if avatar:
        _paste_circle(image, avatar, (left + 28, top + 28, left + 86, top + 86))
    else:
        draw.ellipse((left + 24, top + 22, left + 88, top + 86), fill=(255, 69, 0, 255))
        draw.ellipse((left + 42, top + 44, left + 48, top + 50), fill=(255, 255, 255, 255))
        draw.ellipse((left + 64, top + 44, left + 70, top + 50), fill=(255, 255, 255, 255))
        draw.arc((left + 43, top + 40, left + 69, top + 68), 15, 165, fill=(255, 255, 255, 255), width=3)
    name_x = left + 100
    draw.text((name_x, top + 25), username, fill=(35, 35, 35), font=username_font)
    name_width = int(draw.textlength(username, font=username_font))
    verified = _asset(asset_dir / "verified.png", (17, 17))
    if verified:
        image.alpha_composite(verified, (name_x + name_width + 10, top + 32))
    else:
        draw.ellipse((name_x + name_width + 10, top + 32, name_x + name_width + 27, top + 49), fill=(38, 132, 255, 255))
    badge_x = name_x
    fallback_badges = ((255, 69, 0, 255), (255, 190, 0, 255), (76, 175, 80, 255), (145, 95, 220, 255))
    for index, color in enumerate(fallback_badges, 1):
        badge = _asset(asset_dir / f"badge-{index}.png", (25, 25))
        if badge:
            image.alpha_composite(badge, (badge_x, top + 78))
        else:
            draw.ellipse((badge_x, top + 78, badge_x + 25, top + 103), fill=color)
        badge_x += 34
    draw.text((right - 52, top + 32), "···", fill=(100, 100, 100), font=username_font)

    # The narration contains the complete story summary. The description is
    # deliberately shorter metadata, so using it here can leave the card
    # with only a headline and a large empty body area.
    draw.multiline_text((left + 28, top + 135), "\n".join(lines), fill=(20, 20, 20), font=body_font, spacing=4)
    draw.line((left + 28, bottom - 72, right - 28, bottom - 72), fill=(225, 225, 225), width=2)
    footer_y = bottom - 51
    like_icon = _asset(asset_dir / "like.png", (20, 20))
    comment_icon = _asset(asset_dir / "comment.png", (20, 20))
    if like_icon:
        image.alpha_composite(like_icon, (left + 30, footer_y))
    else:
        # Small outline heart, matching the light-gray Reddit footer icon.
        draw.arc((left + 30, footer_y + 1, left + 40, footer_y + 11), 180, 360, fill=(145, 145, 145), width=2)
        draw.arc((left + 39, footer_y + 1, left + 49, footer_y + 11), 180, 360, fill=(145, 145, 145), width=2)
        draw.line((left + 30, footer_y + 6, left + 40, footer_y + 18, left + 49, footer_y + 6), fill=(145, 145, 145), width=2)
    if comment_icon:
        image.alpha_composite(comment_icon, (left + 143, footer_y))
    else:
        draw.rounded_rectangle((left + 143, footer_y + 1, left + 161, footer_y + 14), radius=5, outline=(145, 145, 145), width=2)
        draw.line((left + 147, footer_y + 13, left + 145, footer_y + 18, left + 152, footer_y + 14), fill=(145, 145, 145), width=2)
    draw.text((left + 56, bottom - 48), "99+", fill=(120, 120, 120), font=small)
    draw.text((left + 169, bottom - 48), "99+", fill=(120, 120, 120), font=small)
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
            # Keep the proven narration-aligned timing. The opening card is a
            # visual layer and must not rewrite subtitle timestamps.
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
