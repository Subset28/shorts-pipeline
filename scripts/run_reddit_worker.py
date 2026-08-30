#!/usr/bin/env python3
"""Publish confirmed Reddit items to public YouTube, retrying on the next run."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/Users/abba/shorts-pipeline/.env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(
    {
        "TOPIC_LIMIT": "20",
        "REDDIT_APPROVED_FILE": "/Users/abba/shorts-pipeline/data/reddit_candidates.json",
        "OUTPUT_DIR": "/Users/abba/shorts-pipeline/output",
        "DATA_DIR": "/Users/abba/shorts-pipeline/data",
        "YOUTUBE_CLIENT_SECRETS": "/Users/abba/shorts-pipeline/client_secrets.json",
        "YOUTUBE_TOKEN_FILE": "/Users/abba/shorts-pipeline/token.json",
        "REDDIT_BACKGROUND_DIR": "/Users/abba/shorts-pipeline/data/backgrounds/minecraft_parkour_chunks",
    }
)

from shorts_pipeline.cli import run
from shorts_pipeline.history import load_seen


def main() -> None:
    candidates = json.loads(Path(os.environ["REDDIT_APPROVED_FILE"]).read_text())
    urls = {item["source"]["url"] for item in candidates if item["source"].get("reuse_permission") is True}
    seen = load_seen(Path(os.environ["DATA_DIR"]) / "seen_sources.json")
    remaining = len(urls - seen)
    print(f"confirmed={len(urls)} remaining={remaining}", flush=True)
    for _ in range(remaining):
        run(reddit_only=True, youtube_only=True)


if __name__ == "__main__":
    main()
