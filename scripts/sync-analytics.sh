#!/bin/sh
set -eu

REMOTE_HOST=${ANALYTICS_REMOTE_HOST:-synology}
REMOTE_DIR=${ANALYTICS_REMOTE_DIR:-/volume1/docker/shorts-pipeline/data/analytics}
LOCAL_DIR=${ANALYTICS_LOCAL_DIR:-/Users/abba/shorts-pipeline/data}

ssh -o BatchMode=yes "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"

files=""
for name in analytics_report.json youtube_analytics.json youtube_weekly_report.json tuning_log.md; do
    path="$LOCAL_DIR/$name"
    if [ -f "$path" ]; then
        files="$files $path"
    fi
done

if [ -z "$files" ]; then
    echo "No analytics artifacts available to sync" >&2
    exit 0
fi

# Explicit allowlist: credentials, tokens, and environment files are never copied.
scp -O -q $files "$REMOTE_HOST:$REMOTE_DIR/"
echo "Synced analytics artifacts to $REMOTE_HOST:$REMOTE_DIR"
