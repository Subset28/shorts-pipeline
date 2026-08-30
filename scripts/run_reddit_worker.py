#!/usr/bin/env python3
"""Publish confirmed Reddit items to public YouTube, retrying on the next run."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/Users/abba/shorts-pipeline/.env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PATH"] = "/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:" + os.environ.get("PATH", "")
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

from shorts_pipeline.cli import run_worker


def main() -> None:
    run_worker(reddit_only=True, youtube_only=True, interval_hours=6.0)


if __name__ == "__main__":
    main()
