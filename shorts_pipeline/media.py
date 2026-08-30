from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import httpx


def _video_candidates(directory: Path) -> list[Path]:
    """Return only non-empty local video files usable by FFmpeg."""
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.glob("*")
        if path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"} and path.is_file() and path.stat().st_size > 0
    )


def select_background(directory: Path, key: str, fallback: Path | None = None) -> Path | None:
    """Choose a stable background from the locally approved footage library."""
    candidates = _video_candidates(directory)
    if candidates:
        index = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % len(candidates)
        return candidates[index]
    return fallback if fallback and fallback.exists() else None


def _manifest_categories(manifest: Path | None) -> dict[str, str]:
    if not manifest or not manifest.exists():
        return {}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return {item["filename"]: item.get("category", "") for item in payload.get("assets", [])}


def _background_category(category: str) -> str:
    """Map editorial lanes to the asset-catalog categories they consume."""
    return {
        "AI News": "AI",
        "Cyber": "Cybersecurity",
        # The catalog deliberately has neutral motion footage for market
        # explainers; avoid visually claiming that a finance story is AI or
        # aerospace news when no finance-specific reel is available.
        "Finance": "General",
    }.get(category, category)


def select_backgrounds(
    directory: Path,
    key: str,
    limit: int = 3,
    category: str | None = None,
    provenance: str | None = None,
    manifest: Path | None = None,
) -> list[Path]:
    """Return a stable, rotated set of approved footage for a short reel.

    Category matches are preferred when the manifest supplies them; if a
    category has no local matches, the full local library remains available.
    """
    candidates = _video_candidates(directory)
    if not candidates:
        return []
    if category:
        categories = _manifest_categories(manifest)
        target_category = _background_category(category)
        matching = [
            path for path in candidates if categories.get(path.name, "").casefold() == target_category.casefold()
        ]
        if matching:
            candidates = matching
    selection_key = "|".join(part for part in (key, category, provenance) if part)
    start = int(hashlib.sha256(selection_key.encode("utf-8")).hexdigest()[:8], 16) % len(candidates)
    rotated = candidates[start:] + candidates[:start]
    return rotated[: max(1, min(limit, len(rotated)))]


def build_background_reel(
    sources: list[Path],
    output: Path,
    seconds_per_clip: float = 3.0,
    variation_key: str = "",
    duration: float = 60.0,
) -> Path | None:
    """Create a long, varied silent reel instead of a short repeating loop."""
    if not sources:
        return sources[0] if sources else None
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    labels = []
    transition = min(0.18, max(0.0, seconds_per_clip / 4))
    seed = int(hashlib.sha256(variation_key.encode("utf-8")).hexdigest()[:8], 16) if variation_key else 0
    usable_segment_length = max(seconds_per_clip - transition, 0.1)
    segment_count = max(1, math.ceil(max(duration, seconds_per_clip) / usable_segment_length))
    start_index = seed % len(sources)
    for index in range(segment_count):
        label = f"v{index}"
        # Every segment gets a different crop/offset even when the category
        # has only one or two approved source videos. Keep a safe margin so
        # the small deterministic pan never asks crop for a negative offset.
        offset = ((seed >> (index * 5 % 24)) + index * 3) % 7
        x_bias = ((seed >> (index * 3 % 24)) % 5) / 10
        y_bias = ((seed >> (index * 4 % 24)) % 5) / 10
        x_position = 0.1 + x_bias * 0.8
        y_position = 0.1 + y_bias * 0.8
        filters.append(
            f"[{index}:v]trim=start={offset},setpts=PTS-STARTPTS,"
            f"crop=iw*0.94:ih*0.94:x=(iw-ow)*({x_position:.3f}+0.04*sin(2*PI*t/{seconds_per_clip:.3f})):"
            f"y=(ih-oh)*({y_position:.3f}+0.04*sin(2*PI*t/{seconds_per_clip:.3f}+PI/2)),"
            f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
            f"unsharp=5:5:0.35:5:5:0,"
            f"setsar=1,fps=30,trim=duration={seconds_per_clip},setpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")
    if transition:
        current = labels[0]
        for index in range(1, segment_count):
            next_label = f"[x{index}]"
            offset = index * usable_segment_length
            filters.append(
                f"{current}{labels[index]}xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}{next_label}"
            )
            current = next_label
        final_label = current
    else:
        filters.append("".join(labels) + f"concat=n={segment_count}:v=1:a=0[v]")
        final_label = "[v]"
    command = ["ffmpeg", "-y"]
    selected_sources = [sources[(start_index + index) % len(sources)] for index in range(segment_count)]
    for source in selected_sources:
        command += ["-stream_loop", "-1", "-i", str(source)]
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        final_label,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
    return output


def download_rights_cleared_source(url: str, output_dir: Path) -> Path:
    """Download a user-authorized source with yt-dlp.

    This adapter deliberately requires an explicit URL and is not used for
    discovery. Callers must maintain rights/provenance for downloaded media.
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp is required for source-media downloads")
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "source.%(ext)s")
    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "--format", "bv*+ba/b", "--merge-output-format", "mp4", "--output", template, url],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    candidates = sorted(output_dir.glob("source.*"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError(f"yt-dlp completed without producing media: {result.stderr[-300:]}")
    return candidates[0]


def ensure_background_video(url: str, path: Path) -> Path | None:
    """Cache a configured public-domain/direct media URL for background footage."""
    if path.exists() and path.stat().st_size:
        return path
    if not url:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        temporary.replace(path)
        return path
    except (OSError, httpx.HTTPError) as exc:
        print(f"Background footage unavailable; using generated card: {exc}")
        temporary.unlink(missing_ok=True)
        return None


def split_authorized_clip(source: Path, output_dir: Path, parts: int = 4) -> list[Path]:
    """Split a user-authorized clip into bounded, independently playable parts."""
    if parts not in {2, 3, 4}:
        raise ValueError("parts must be 2, 3, or 4")
    if not source.exists():
        raise FileNotFoundError(source)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required")
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    duration = float(probe.stdout.strip())
    output_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for index in range(parts):
        start = duration * index / parts
        length = duration / parts
        target = output_dir / f"part-{index + 1}-of-{parts}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source),
                "-t",
                f"{length:.3f}",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(target),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        result.append(target)
    return result
