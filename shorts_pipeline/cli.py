from __future__ import annotations

import argparse
import time

from .config import load_settings
from .history import load_seen, mark_seen
from .llm import create_package
from .publish import save_manifest, upload_tiktok, upload_youtube
from .render import render_video
from .sources import discover_topics
from .tts import synthesize


def run(force_dry_run: bool = False) -> int:
    settings = load_settings()
    dry_run = force_dry_run or settings.dry_run
    topics = discover_topics(settings.topic_limit)
    if not topics:
        raise RuntimeError("No source-backed topics were discovered")
    seen_path = settings.data_dir / "seen_sources.json"
    seen = load_seen(seen_path)
    topic = next((item for item in topics if item.sources[0].url not in seen), topics[0])
    package = create_package(topic, settings.openai_api_key, settings.openai_model)
    audio = synthesize(package.narration, settings, settings.output_dir / "narration.mp3")
    video = render_video(package, settings.output_dir, audio)
    manifest = save_manifest(package, video, settings.output_dir)
    mark_seen(seen_path, topic.sources[0].url)
    print(f"Created {manifest}")
    if dry_run:
        print("Dry run: YouTube and TikTok uploads skipped")
        return 0
    youtube_id = upload_youtube(video, package, settings.youtube_client_secrets, settings.youtube_token_file, settings.youtube_privacy_status)
    tiktok_id = upload_tiktok(video, package, settings.tiktok_access_token, settings.tiktok_privacy_level)
    print(f"Published YouTube={youtube_id} TikTok={tiktok_id}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--daemon", action="store_true")
    run_parser.add_argument("--interval-hours", type=float, default=24.0)
    args = parser.parse_args()
    if args.daemon:
        while True:
            run(force_dry_run=args.dry_run)
            time.sleep(max(args.interval_hours, 0.25) * 3600)
    raise SystemExit(run(force_dry_run=args.dry_run))
