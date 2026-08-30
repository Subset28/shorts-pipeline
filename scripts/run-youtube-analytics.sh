#!/bin/sh
set -eu
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"
cd /Volumes/n2me/Developer/shorts-pipeline
export DATA_DIR="/Users/abba/shorts-pipeline/data"
export YOUTUBE_CLIENT_SECRETS="/Users/abba/shorts-pipeline/client_secrets.json"
export YOUTUBE_TOKEN_FILE="/Users/abba/shorts-pipeline/token.json"
export YOUTUBE_ANALYTICS_TOKEN_FILE="/Users/abba/shorts-pipeline/youtube_analytics_token.json"
exec /Users/abba/shorts-pipeline/.venv/bin/python -m shorts_pipeline analytics "$@"
