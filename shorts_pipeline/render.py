from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScriptPackage
from .resources import ffmpeg_resource_args

AUDIO_NORMALIZATION_FILTER = "loudnorm=I=-16:TP=-1.5:LRA=11"


def _render_size() -> tuple[int, int]:
    raw_size = os.environ.get("RENDER_SIZE", "1080x1920")
    try:
        width, height = (int(value) for value in raw_size.lower().split("x", maxsplit=1))
    except ValueError as exc:
        raise ValueError("RENDER_SIZE must be WIDTHxHEIGHT") from exc
    if (width, height) not in {(720, 1280), (1080, 1920)}:
        raise ValueError("RENDER_SIZE must be 720x1280 or 1080x1920")
    return width, height


def _estimated_duration(text: str) -> float:
    return max(10.0, min(60.0, len(text.split()) / 2.5))


def _audio_duration(audio: Path | None) -> float | None:
    """Probe generated narration so video length follows the actual voice track."""
    if not audio or not audio.exists():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return max(0.0, float(result.stdout.strip()))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _render_duration(text: str, audio: Path | None) -> float:
    """Use measured narration duration, falling back to the text estimate."""
    measured = _audio_duration(audio)
    if measured is None:
        return _estimated_duration(text)
    return max(10.0, min(60.0, measured))


def _caption_filter(captions: Path, margin_v: int = 430) -> str:
    ass_file = captions.with_suffix(".ass") if captions.suffix.lower() == ".srt" else captions
    caption_file = str(ass_file.resolve()).replace("\\", "/").replace(":", r"\:")
    if ass_file.exists():
        return f"subtitles='{caption_file}':force_style='MarginV={margin_v}'"
    style = "FontName=Arial,FontSize=68,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=5,Shadow=2,Bold=1,Alignment=2,MarginL=65,MarginR=65,MarginV=430"
    return f"subtitles='{caption_file}':original_size=1080x1920:force_style='{style}'"


def _font_candidates(bold: bool = False) -> tuple[str, ...]:
    if bold:
        return (
            "arialbd.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        )
    return (
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _font_candidates(bold):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_thumbnail(package: ScriptPackage, path: Path) -> Path:
    """Create a readable custom thumbnail for YouTube packaging."""
    image = Image.new("RGB", (1280, 720), (8, 16, 32))
    draw = ImageDraw.Draw(image)
    for y in range(720):
        shade = int(8 + (y / 720) * 18)
        draw.line((0, y, 1280, y), fill=(shade, shade + 8, shade + 24))
    draw.rectangle((0, 0, 24, 720), fill=(255, 92, 38))
    draw.rounded_rectangle((72, 70, 370, 122), radius=18, fill=(255, 92, 38))
    draw.text((96, 82), "SIGNAL LAB", fill="white", font=_font(28, bold=True))
    draw.text((78, 610), package.category.upper(), fill=(180, 205, 230), font=_font(26, bold=True))
    hook = " ".join(package.hook.split()).strip()
    lines = textwrap.wrap(hook, width=24)[:3] or ["TECHNOLOGY EXPLAINED"]
    draw.multiline_text(
        (78, 205),
        "\n".join(lines),
        fill="white",
        font=_font(72, bold=True),
        spacing=14,
        stroke_width=3,
        stroke_fill=(0, 0, 0),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=92, optimize=True)
    return path


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
    font = _font(58 if transparent else 54, bold=True)
    if transparent and show_hook:
        lines = textwrap.wrap(package.hook.upper(), width=22)[:3]
        hook_text = "\n".join(lines)
        bounds = draw.multiline_textbbox((0, 0), hook_text, font=font, spacing=8, stroke_width=2)
        panel = (40, 145, min(1040, bounds[2] + 110), bounds[3] - bounds[1] + 220)
        draw.rounded_rectangle(panel, radius=28, fill=(5, 10, 22, 205), outline=(255, 255, 255, 80), width=2)
        draw.rounded_rectangle((panel[0], panel[1], panel[0] + 12, panel[3]), radius=6, fill=(255, 92, 38, 255))
        draw.multiline_text(
            (72, 205), hook_text, fill="white", font=font, spacing=8, stroke_width=2, stroke_fill=(0, 0, 0, 230)
        )
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
    # Match the reference treatment: a compact post floating over the game,
    # rather than a full-width panel that dominates the opening frame.
    left, right = 35, 1045
    top = 650
    story = (package.card_text or package.title).strip()
    if len(story.split()) < 12:
        story_match = re.search(r"Here's what happened:\s*(.*?)(?:\s+The useful part|\Z)", package.narration, re.S)
        narrated_story = story_match.group(1).strip() if story_match else ""
        # Keep the card punchy and avoid ending on a clipped clause.
        first_sentence = re.split(r"(?<=[.!?])\s+", narrated_story, maxsplit=1)[0]
        story = first_sentence or story
    story = re.sub(r"^\[FICTIONAL REVIEW DEMO\]\s*", "", story)
    lines = textwrap.wrap(story, width=45)[:9]
    # Let the post card flow with the text. The old fixed 490px minimum left
    # conspicuous empty space when a post had a short title.
    bottom = max(top + 365, top + 150 + (len(lines) * 48) + 90)
    draw.rounded_rectangle(
        (left, top, right, bottom), radius=22, fill=(250, 250, 250, 252), outline=(215, 215, 215, 255), width=3
    )

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
    award_files = sorted((asset_dir / "awards").glob("*.png"))
    award_files += sorted((asset_dir / "awards").glob("*.gif"))
    seed_bytes = hashlib.sha256((package.title + "|" + "|".join(package.sources)).encode("utf-8")).digest()
    seed = int.from_bytes(seed_bytes[:4], "big")
    selected_awards = (
        [award_files[(seed + (index * 17)) % len(award_files)] for index in range(8)] if award_files else []
    )
    animated_files = [award for award in award_files if award.suffix.lower() == ".gif"]
    if selected_awards and animated_files:
        # Keep motion present in every Reddit opening while varying which
        # award animates and which static awards surround it.
        animated_slot = seed % len(selected_awards)
        selected_awards[animated_slot] = animated_files[(seed // len(selected_awards)) % len(animated_files)]
    animated_awards: list[tuple[Path, int]] = []
    for index in range(8):
        color = fallback_badges[index % len(fallback_badges)]
        badge = (
            _asset(selected_awards[index], (25, 25))
            if selected_awards
            else _asset(asset_dir / f"badge-{index + 1}.png", (25, 25))
        )
        if badge:
            image.alpha_composite(badge, (badge_x, top + 78))
        else:
            draw.ellipse((badge_x, top + 78, badge_x + 25, top + 103), fill=color)
        if selected_awards and selected_awards[index].suffix.lower() == ".gif":
            animated_awards.append((selected_awards[index], badge_x))
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
    share_icon = _asset(asset_dir / "share.png", (20, 20))
    if like_icon:
        image.alpha_composite(like_icon, (left + 30, footer_y))
    else:
        # Small outline heart, matching the light-gray Reddit footer icon.
        draw.arc((left + 30, footer_y + 1, left + 40, footer_y + 11), 180, 360, fill=(145, 145, 145), width=2)
        draw.arc((left + 39, footer_y + 1, left + 49, footer_y + 11), 180, 360, fill=(145, 145, 145), width=2)
        draw.line(
            (left + 30, footer_y + 6, left + 40, footer_y + 18, left + 49, footer_y + 6), fill=(145, 145, 145), width=2
        )
    if comment_icon:
        image.alpha_composite(comment_icon, (left + 143, footer_y))
    else:
        draw.rounded_rectangle(
            (left + 143, footer_y + 1, left + 161, footer_y + 14), radius=5, outline=(145, 145, 145), width=2
        )
        draw.line(
            (left + 147, footer_y + 13, left + 145, footer_y + 18, left + 152, footer_y + 14),
            fill=(145, 145, 145),
            width=2,
        )
    if share_icon:
        image.alpha_composite(share_icon, (right - 98, footer_y))
    else:
        draw.line((right - 91, footer_y + 17, right - 91, footer_y + 2), fill=(145, 145, 145), width=2)
        draw.line((right - 91, footer_y + 2, right - 97, footer_y + 8), fill=(145, 145, 145), width=2)
        draw.line((right - 91, footer_y + 2, right - 85, footer_y + 8), fill=(145, 145, 145), width=2)
    draw.text((right - 66, bottom - 48), "Share", fill=(120, 120, 120), font=small)
    draw.text((left + 56, bottom - 48), "99+", fill=(120, 120, 120), font=small)
    draw.text((left + 169, bottom - 48), "99+", fill=(120, 120, 120), font=small)
    image.save(path)
    if animated_awards:
        frames = []
        for frame_index in range(8):
            frame = image.copy()
            for award_path, x in animated_awards:
                try:
                    with Image.open(award_path) as award:
                        award.seek(frame_index % max(1, getattr(award, "n_frames", 1)))
                        badge_frame = award.convert("RGBA")
                        badge_frame.thumbnail((25, 25), Image.Resampling.LANCZOS)
                        frame.alpha_composite(badge_frame, (x, top + 78))
                except (OSError, EOFError):
                    continue
            frames.append(frame)
        frames[0].save(
            path.with_suffix(".gif"), save_all=True, append_images=frames[1:], duration=120, loop=0, disposal=2
        )


def _story_system_nodes(category: str, story_text: str) -> tuple[str, str, str] | None:
    normalized = category.lower()
    text = story_text.lower()
    if "cyber" in normalized:
        if re.search(r"\b(spf|dkim|dmarc|email|mail|sender|inbox)\b", text):
            return ("SENDER", "DNS POLICY", "INBOX")
        if re.search(r"\b(identity|authentication|login|account|tenant|m365|oauth)\b", text):
            return ("USER", "IDENTITY", "CLOUD")
        if re.search(r"\b(malware|ransomware|phishing|endpoint|payload)\b", text):
            return ("ATTACKER", "ENDPOINT", "NETWORK")
        if re.search(r"\b(dns|firewall|network|packet|proxy)\b", text):
            return ("CLIENT", "NETWORK", "SERVICE")
    if "ai" in normalized or "ml" in normalized or "machine" in normalized:
        if re.search(r"\b(image|vision|camera|pixel)\b", text):
            return ("IMAGE", "MODEL", "PREDICTION")
        if re.search(r"\b(train|training|dataset|fine-tun)\b", text):
            return ("DATA", "TRAINING", "MODEL")
        if re.search(r"\b(model|inference|agent|neural)\b", text):
            return ("INPUT", "MODEL", "OUTPUT")
    if "cs" in normalized or "software" in normalized or "sysadmin" in normalized:
        if re.search(r"\b(powershell|script|automation|command)\b", text):
            return ("INPUT", "SCRIPT", "SYSTEM")
        if re.search(r"\b(server|vm|host|storage)\b", text):
            return ("CLIENT", "SERVER", "STORAGE")
        if re.search(r"\b(support|ticket|vendor|helpdesk)\b", text):
            return ("USER", "SUPPORT", "VENDOR")
        if re.search(r"\b(code|bug|deploy|production)\b", text):
            return ("CODE", "DEPLOY", "PRODUCTION")
    if "aerospace" in normalized:
        if re.search(r"\b(engine|fluid|fuel|propulsion|thrust)\b", text):
            return ("FUEL", "ENGINE", "THRUST")
        if re.search(r"\b(sensor|telemetry|avionics)\b", text):
            return ("SENSOR", "TELEMETRY", "CONTROL")
    return None


def _scene_excerpt(text: str, limit: int = 150) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    words = cleaned[: limit + 1].split()
    shortened = " ".join(words[:-1]).rstrip(" ,;:-")
    return shortened + "…"


def _story_scene_copy(package: ScriptPackage) -> tuple[str, str, str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", package.narration) if part.strip()]
    incident = package.card_text or package.title
    detail = sentences[len(sentences) // 2] if sentences else package.hook
    outcome = sentences[-1] if sentences else package.hook
    return tuple(_scene_excerpt(item) for item in (incident, detail, outcome))


def _story_outcome_kicker(outcome: str) -> str:
    if re.search(r"\b(lesson|takeaway)\b", outcome, re.IGNORECASE):
        return "TAKEAWAY"
    if re.search(
        r"\b(outcome|fixed|resolved|recovered|restored|result|ended up|turned out|finally)\b", outcome, re.IGNORECASE
    ):
        return "OUTCOME"
    return "FINAL DETAIL"


def _scene_lines(body: str, width: int = 31, limit: int = 4) -> list[str]:
    lines = textwrap.wrap(body, width=width)
    if len(lines) <= limit:
        return lines
    visible = lines[:limit]
    visible[-1] = visible[-1][: width - 1].rstrip(" ,.;:-") + "…"
    return visible


def _draw_story_scene(
    package: ScriptPackage,
    path: Path,
    kicker: str,
    body: str,
    nodes: tuple[str, str, str] | None = None,
) -> None:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    accent = (68, 214, 255, 255) if "cyber" in package.category.lower() else (255, 92, 38, 255)
    draw.rounded_rectangle((42, 150, 1038, 635), radius=34, fill=(5, 10, 22, 232), outline=(255, 255, 255, 70), width=2)
    draw.rounded_rectangle((42, 150, 55, 635), radius=6, fill=accent)
    draw.rounded_rectangle((78, 188, 385, 238), radius=18, fill=accent)
    draw.text((98, 198), kicker, fill=(5, 10, 22), font=_font(25, bold=True))
    draw.multiline_text(
        (78, 290),
        "\n".join(_scene_lines(body)),
        fill="white",
        font=_font(50, bold=True),
        spacing=12,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 180),
    )
    draw.text((78, 575), "SOURCE-BACKED • REDDIT", fill=(170, 190, 215), font=_font(22, bold=True))
    if nodes:
        node_y = 750
        for index, label in enumerate(nodes):
            left = 48 + (index * 350)
            right = left + 284
            node_fill = (110, 32, 52, 235) if index == 1 else (8, 25, 46, 235)
            draw.rounded_rectangle(
                (left, node_y, right, node_y + 150), radius=28, fill=node_fill, outline=accent, width=4
            )
            width = draw.textlength(label, font=_font(27, bold=True))
            draw.text((left + ((284 - width) / 2), node_y + 57), label, fill="white", font=_font(27, bold=True))
            if index < 2:
                draw.line((right + 12, node_y + 75, right + 54, node_y + 75), fill=accent, width=8)
                draw.polygon(
                    ((right + 54, node_y + 75), (right + 36, node_y + 61), (right + 36, node_y + 89)), fill=accent
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _story_visuals(package: ScriptPackage, output_dir: Path) -> list[Path]:
    incident, detail, outcome = _story_scene_copy(package)
    story_text = f"{package.title} {package.card_text} {package.narration}"
    records = (
        ("WHAT HAPPENED", incident, None, "story-incident.png"),
        ("SYSTEM VIEW", detail, _story_system_nodes(package.category, story_text), "story-system.png"),
        (_story_outcome_kicker(outcome), outcome, None, "story-outcome.png"),
    )
    paths = []
    for kicker, body, nodes, filename in records:
        path = output_dir / filename
        _draw_story_scene(package, path, kicker, body, nodes)
        paths.append(path)
    return paths


def _reddit_opening(card: Path, reddit_card: Path, path: Path) -> Path:
    with Image.open(card) as source:
        opening = source.convert("RGBA")
    with Image.open(reddit_card) as source:
        opening.alpha_composite(source.convert("RGBA"))
    opening.save(path)
    return path


def _story_timeline(
    visuals: list[Path], opening: Path, background: Path, path: Path, duration: float, width: int, height: int
) -> Path:
    scene_start = min(4.0, duration * 0.4)
    segment = max(0.1, (duration - scene_start) / 3)
    clips = []
    scenes = [(opening, scene_start), *((visual, segment) for visual in visuals)]
    for index, (visual, scene_duration) in enumerate(scenes):
        clip = path.with_name(f"{path.stem}-{index}.mp4")
        command = [
            "ffmpeg",
            "-y",
            *ffmpeg_resource_args(1),
            "-stream_loop",
            "-1",
            "-i",
            str(background),
            "-loop",
            "1",
            "-i",
            str(visual),
            "-t",
            f"{scene_duration:.3f}",
            "-filter_complex",
            "[0:v]crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:"
            f"(ih-min(ih\\,iw*16/9))/2,scale={width}:{height}:flags=bicubic,"
            "eq=saturation=1.15:contrast=1.08:brightness=-0.04[bg];"
            f"[1:v]scale={width}:{height}[panel];[bg][panel]overlay=0:0[v]",
            "-map",
            "[v]",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-x264-params",
            "threads=1:lookahead_threads=1",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
        clips.append(clip)
    playlist = path.with_suffix(".concat.txt")
    playlist.write_text("".join(f"file '{clip.name}'\n" for clip in clips), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            *ffmpeg_resource_args(1),
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(playlist),
            "-c",
            "copy",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return path


def render_video(
    package: ScriptPackage,
    output_dir: Path,
    audio: Path | None = None,
    captions: Path | None = None,
    background: Path | None = None,
) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    card = output_dir / "card.png"
    try:
        _card(
            package,
            card,
            transparent=bool(background and background.exists()),
            show_hook=package.format_name != "reddit_story",
        )
    except OSError:
        # Windows installations can lack Arial; the video still renders with
        # a plain card rather than silently skipping the artifact.
        Image.new("RGB", (1080, 1920), (12, 20, 38)).save(card)
    output = output_dir / "short.mp4"
    duration = _render_duration(package.narration, audio)
    width, height = _render_size()
    output_scale = f"scale={width}:{height}"
    if background and background.exists():
        if package.format_name == "reddit_story":
            reddit_card = output_dir / "reddit-post-card.png"
            _reddit_post_card(package, reddit_card)
            opening = _reddit_opening(card, reddit_card, output_dir / "reddit-opening.png")
            story_visuals = _story_visuals(package, output_dir)
            timeline = _story_timeline(
                story_visuals, opening, background, output_dir / "story-timeline.mp4", duration, width, height
            )
            command = ["ffmpeg", "-y", *ffmpeg_resource_args(1), "-i", str(timeline)]
            if audio:
                command += ["-i", str(audio)]
            else:
                command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            command += [
                "-vf",
                _caption_filter(captions) if captions and captions.exists() else "null",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-t",
                str(duration),
                "-r",
                "30",
                "-c:v",
                "libx264",
                "-x264-params",
                "threads=1:lookahead_threads=1",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "").strip()
                detail = detail[-1000:] if detail else "no diagnostic output"
                raise RuntimeError(f"FFmpeg render failed with exit {exc.returncode}: {detail}") from exc
            return output
        command = [
            "ffmpeg",
            "-y",
            *ffmpeg_resource_args(1),
            "-stream_loop",
            "-1",
            "-i",
            str(background),
            "-loop",
            "1",
            "-i",
            str(card),
        ]
        audio_index = 2
        if audio:
            command += ["-i", str(audio)]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        # Crop to portrait before scaling so the compositor does not enlarge
        # the entire landscape frame, while bicubic keeps the gameplay clear.
        video_filter = (
            "[0:v]crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:"
            f"(ih-min(ih\\,iw*16/9))/2,scale={width}:{height}:flags=bicubic,"
            "eq=saturation=1.15:contrast=1.08:brightness=-0.04[bg];"
            f"[1:v]{output_scale}[opening];[bg][opening]overlay=0:0"
        )
        if captions and captions.exists():
            # Keep the proven narration-aligned timing. The opening card is a
            # visual layer and must not rewrite subtitle timestamps.
            video_filter += "," + _caption_filter(captions)
        command += [
            "-filter_complex",
            video_filter + "[v]",
            "-map",
            "[v]",
            "-map",
            f"{audio_index}:a",
            "-t",
            str(duration),
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-x264-params",
            "threads=1:lookahead_threads=1",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
    else:
        command = ["ffmpeg", "-y", *ffmpeg_resource_args(1), "-loop", "1", "-i", str(card)]
        if audio:
            command += ["-i", str(audio), "-shortest"]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(duration)]
        video_filter = output_scale
        if captions and captions.exists():
            video_filter += "," + _caption_filter(captions)
        command += [
            "-vf",
            video_filter,
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-x264-params",
            "threads=1:lookahead_threads=1",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        detail = detail[-1000:] if detail else "no diagnostic output"
        raise RuntimeError(f"FFmpeg render failed with exit {exc.returncode}: {detail}") from exc
    return output
