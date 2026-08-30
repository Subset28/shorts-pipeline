from __future__ import annotations

import argparse
import traceback
import time
from pathlib import Path

from .config import load_settings
from .captions import create_captions
from .history import load_publish_state, load_seen, mark_seen, save_publish_state
from .llm import create_package
from .media import ensure_background_video, split_authorized_clip
from .publish import save_manifest, upload_tiktok, upload_youtube
from .render import render_video
from .sources import discover_topics
from .tts import synthesize
from .telemetry import record_event


def run(force_dry_run: bool = False) -> int:
    settings = load_settings()
    dry_run = force_dry_run or settings.dry_run
    topics = discover_topics(settings.topic_limit)
    if not topics:
        raise RuntimeError("No source-backed topics were discovered")
    seen_path = settings.data_dir / "seen_sources.json"
    publish_path = settings.data_dir / "publish_state.json"
    events_path = settings.data_dir / "events.jsonl"
    seen = load_seen(seen_path)
    topic = next((item for item in topics if item.sources[0].url not in seen), topics[0])
    source_url = topic.sources[0].url
    published = load_publish_state(publish_path).get(source_url, {})
    package = create_package(topic, settings.openai_api_key, settings.openai_model)
    audio = synthesize(package.narration, settings, settings.output_dir / "narration.mp3")
    captions = create_captions(package.narration, audio, settings.output_dir / "captions.srt", settings.caption_model) if settings.captions_enabled else None
    background = ensure_background_video(settings.background_video_url, settings.background_video)
    video = render_video(package, settings.output_dir, audio, captions, background)
    manifest = save_manifest(package, video, settings.output_dir)
    record_event(events_path, "draft_created", source_url=source_url, format_name=package.format_name, title=package.title, video=str(video), dry_run=dry_run)
    print(f"Created {manifest}")
    if dry_run:
        print("Dry run: YouTube and TikTok uploads skipped")
        return 0
    youtube_id = published.get("youtube_id") or upload_youtube(video, package, settings.youtube_client_secrets, settings.youtube_token_file, settings.youtube_privacy_status)
    save_publish_state(publish_path, source_url, youtube_id=youtube_id)
    record_event(events_path, "youtube_published", source_url=source_url, format_name=package.format_name, platform_id=youtube_id)
    tiktok_id = published.get("tiktok_id") or upload_tiktok(video, package, settings.tiktok_access_token, settings.tiktok_privacy_level)
    save_publish_state(publish_path, source_url, tiktok_id=tiktok_id)
    record_event(events_path, "tiktok_published", source_url=source_url, format_name=package.format_name, platform_id=tiktok_id)
    mark_seen(seen_path, source_url)
    print(f"Published YouTube={youtube_id} TikTok={tiktok_id}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--daemon", action="store_true")
    run_parser.add_argument("--interval-hours", type=float, default=24.0)
    split_parser = sub.add_parser("split")
    split_parser.add_argument("--input", required=True)
    split_parser.add_argument("--out", default="output/series")
    split_parser.add_argument("--parts", type=int, default=4)
    args = parser.parse_args()
    if args.command == "split":
        for part in split_authorized_clip(Path(args.input), Path(args.out), args.parts):
            print(part)
        return
    if args.daemon:
        while True:
            try:
                run(force_dry_run=args.dry_run)
            except Exception as exc:
                print(f"Pipeline run failed; will retry: {exc}")
                traceback.print_exc()
            time.sleep(max(args.interval_hours, 0.25) * 3600)
    raise SystemExit(run(force_dry_run=args.dry_run))
