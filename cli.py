from __future__ import annotations

import argparse
import json
import traceback
import time
from dataclasses import replace
from pathlib import Path

from .config import load_settings
from .captions import create_captions
from .analytics import build_report, write_report
from .asset_library import sync_backgrounds
from .history import load_publish_state, load_seen, mark_seen, save_publish_state
from .llm import create_package
from .media import build_background_reel, ensure_background_video, select_backgrounds, split_authorized_clip
from .publish import fetch_tiktok_status, save_manifest, upload_tiktok, upload_youtube
from .render import render_video
from .sources import discover_topics
from .tts import synthesize
from .telemetry import record_event
from .reddit import discover_reddit_topics, load_approved_reddit_topics


def _discover_topics(settings, limit: int, reddit_only: bool = False, private_drafts: bool = False):
    if reddit_only:
        topics = discover_reddit_topics(
            settings.reddit_subreddits,
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            limit,
        )
        if private_drafts:
            # Private review drafts may use discovered posts in memory, while
            # normal publishing continues to require explicit reuse approval.
            topics = [
                replace(topic, sources=(replace(topic.sources[0], reuse_permission=True),))
                for topic in topics
            ]
        return topics
    topics = discover_topics(limit)
    topics.extend(load_approved_reddit_topics(settings.reddit_approved_file))
    return topics


def _next_batch_dir(output_dir: Path) -> Path:
    """Allocate a non-destructive batch directory for experiment history."""
    output_dir.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        candidate = output_dir / f"batch-{index:02d}"
        if not candidate.exists():
            return candidate
        index += 1


def _publish_state_key(source_url: str, variant: int) -> str:
    """Keep legacy variant-zero state compatible while isolating experiments."""
    return source_url if variant == 0 else f"{source_url}#variant={variant}"


def run(force_dry_run: bool = False, topic_override=None, output_dir_override: Path | None = None, variant: int = 0, reddit_only: bool = False, private_drafts: bool = False) -> int:
    settings = load_settings()
    dry_run = force_dry_run or (settings.dry_run and not private_drafts)
    topics = [topic_override] if topic_override else _discover_topics(settings, settings.topic_limit, reddit_only, private_drafts)
    if not topics:
        raise RuntimeError("No source-backed topics were discovered")
    seen_path = settings.data_dir / "seen_sources.json"
    publish_path = settings.data_dir / "publish_state.json"
    events_path = settings.data_dir / "events.jsonl"
    seen = load_seen(seen_path)
    topic = next((item for item in topics if item.sources[0].url not in seen), topics[0])
    source_url = topic.sources[0].url
    output_dir = output_dir_override or settings.output_dir
    package = create_package(topic, settings.openai_api_key, settings.openai_model, variant)
    state_key = _publish_state_key(source_url, package.variant)
    published = load_publish_state(publish_path).get(state_key, {})
    audio = synthesize(package.narration, settings, output_dir / "narration.mp3")
    if not audio or not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("TTS produced no audio; refusing to create a silent short")
    captions = create_captions(package.narration, audio, output_dir / "captions.srt", settings.caption_model) if settings.captions_enabled else None
    fallback_background = ensure_background_video(settings.background_video_url, settings.background_video)
    background_dir = settings.reddit_background_dir if package.format_name == "reddit_story" and settings.reddit_background_dir.exists() else settings.background_dir
    background_sources = select_backgrounds(
        background_dir,
        f"{source_url}|{package.variant}",
        category=package.category if background_dir == settings.background_dir else None,
        manifest=Path("assets/backgrounds.json"),
    )
    if background_sources:
        background = build_background_reel(
            background_sources,
            output_dir / "background-reel.mp4",
            variation_key=f"{source_url}|{package.variant}",
        )
    else:
        background = fallback_background
    video = render_video(package, output_dir, audio, captions, background)
    manifest = save_manifest(package, video, output_dir, background, background_sources)
    record_event(events_path, "draft_created", source_url=source_url, category=package.category, format_name=package.format_name, variant=package.variant, title=package.title, video=str(video), dry_run=dry_run)
    print(f"Created {manifest}")
    if dry_run:
        print("Dry run: YouTube and TikTok uploads skipped")
        return 0
    privacy = "private" if private_drafts else settings.youtube_privacy_status
    youtube_id = published.get("youtube_id") or upload_youtube(video, package, settings.youtube_client_secrets, settings.youtube_token_file, privacy)
    save_publish_state(publish_path, state_key, youtube_id=youtube_id)
    record_event(events_path, "youtube_published", source_url=source_url, category=package.category, format_name=package.format_name, variant=package.variant, platform_id=youtube_id)
    if private_drafts:
        mark_seen(seen_path, source_url)
        print(f"Uploaded private YouTube draft: {youtube_id}")
        return 0
    tiktok_id = published.get("tiktok_id")
    if not tiktok_id:
        tiktok_id = upload_tiktok(video, package, settings.tiktok_access_token, settings.tiktok_privacy_level)
        save_publish_state(publish_path, state_key, tiktok_id=tiktok_id, tiktok_status="PROCESSING_UPLOAD")
        record_event(events_path, "tiktok_upload_started", source_url=source_url, category=package.category, format_name=package.format_name, variant=package.variant, platform_id=tiktok_id)
        print(f"Uploaded to TikTok; processing status pending: {tiktok_id}")
        return 0
    tiktok_status = fetch_tiktok_status(settings.tiktok_access_token, tiktok_id)
    if tiktok_status == "FAILED":
        raise RuntimeError(f"TikTok rejected publish {tiktok_id}")
    if tiktok_status != "PUBLISH_COMPLETE":
        save_publish_state(publish_path, state_key, tiktok_status=tiktok_status)
        record_event(events_path, "tiktok_processing", source_url=source_url, category=package.category, format_name=package.format_name, variant=package.variant, platform_id=tiktok_id, status=tiktok_status)
        print(f"TikTok still processing ({tiktok_status}); will check again next run")
        return 0
    save_publish_state(publish_path, state_key, tiktok_status=tiktok_status)
    record_event(events_path, "tiktok_published", source_url=source_url, category=package.category, format_name=package.format_name, variant=package.variant, platform_id=tiktok_id)
    mark_seen(seen_path, source_url)
    print(f"Published YouTube={youtube_id} TikTok={tiktok_id}")
    return 0


def run_batch(count: int, force_dry_run: bool = False, variants: int = 1) -> int:
    settings = load_settings()
    topics = _discover_topics(settings, max(settings.topic_limit, count))
    if not topics:
        raise RuntimeError("No source-backed topics were discovered; RSS feeds may be unavailable. Check network access and feed health before retrying.")
    seen = load_seen(settings.data_dir / "seen_sources.json")
    unique = []
    selected_urls = set()
    for topic in topics:
        source_url = topic.sources[0].url
        if source_url not in seen and source_url not in selected_urls:
            unique.append(topic)
            selected_urls.add(source_url)
        if len(unique) == count:
            break
    if len(unique) < count:
        raise RuntimeError(f"Only {len(unique)} unseen topics available; requested {count}")
    batch_dir = _next_batch_dir(settings.output_dir)
    for index, topic in enumerate(unique, 1):
        for variant in range(max(1, variants)):
            suffix = f"-v{variant + 1:02d}" if variants > 1 else ""
            run(force_dry_run=force_dry_run, topic_override=topic, output_dir_override=batch_dir / f"item-{index:02d}{suffix}", variant=variant)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--reddit-only", action="store_true")
    run_parser.add_argument("--private-drafts", action="store_true", help="Generate discovered Reddit stories and upload them privately to YouTube")
    run_parser.add_argument("--daemon", action="store_true")
    run_parser.add_argument("--interval-hours", type=float, default=24.0)
    split_parser = sub.add_parser("split")
    split_parser.add_argument("--input", required=True)
    split_parser.add_argument("--out", default="output/series")
    split_parser.add_argument("--parts", type=int, default=4)
    batch_parser = sub.add_parser("batch")
    batch_parser.add_argument("--count", type=int, default=3)
    batch_parser.add_argument("--dry-run", action="store_true")
    batch_parser.add_argument("--variants", type=int, default=1, help="Treatments per source for controlled hook/format experiments")
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--metrics", required=True, help="CSV export with source_url, platform, and views columns")
    report_parser.add_argument("--events", default="data/events.jsonl")
    report_parser.add_argument("--out", default="data/analytics_report.json")
    assets_parser = sub.add_parser("backgrounds")
    assets_parser.add_argument("--manifest", default="assets/backgrounds.json")
    assets_parser.add_argument("--out", default="data/backgrounds")
    reddit_parser = sub.add_parser("reddit")
    reddit_parser.add_argument("--out", default="data/reddit_candidates.json")
    reddit_parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if args.command == "split":
        for part in split_authorized_clip(Path(args.input), Path(args.out), args.parts):
            print(part)
        return
    if args.command == "batch":
        raise SystemExit(run_batch(max(1, args.count), force_dry_run=args.dry_run, variants=max(1, args.variants)))
    if args.command == "report":
        report = build_report(Path(args.events), Path(args.metrics))
        output = write_report(report, Path(args.out))
        print(f"Wrote {output} ({report['matched_rows']} matched rows, {report['unmatched_rows']} unmatched)")
        return
    if args.command == "backgrounds":
        for path in sync_backgrounds(Path(args.manifest), Path(args.out)):
            print(path)
        return
    if args.command == "reddit":
        settings = load_settings()
        topics = discover_reddit_topics(settings.reddit_subreddits, settings.reddit_client_id, settings.reddit_client_secret, settings.reddit_user_agent, max(1, args.count))
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps([{"title": topic.title, "source": topic.sources[0].__dict__, "score": topic.score} for topic in topics], indent=2), encoding="utf-8")
        print(f"Wrote {output} ({len(topics)} candidates; none are cleared for publishing)")
        return
    if args.daemon:
        while True:
            try:
                run(force_dry_run=args.dry_run, reddit_only=args.reddit_only, private_drafts=args.private_drafts)
            except Exception as exc:
                print(f"Pipeline run failed; will retry: {exc}")
                traceback.print_exc()
            time.sleep(max(args.interval_hours, 0.25) * 3600)
        raise SystemExit(run(force_dry_run=args.dry_run, reddit_only=args.reddit_only, private_drafts=args.private_drafts))
