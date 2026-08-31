#!/bin/sh
set -eu

repo_dir=${PIPELINE_REPO_DIR:-/Volumes/n2me/Developer/shorts-pipeline}
agent_dir=${LAUNCH_AGENT_DIR:-/Users/abba/Library/LaunchAgents}
log_dir=${LAUNCH_LOG_DIR:-/Users/abba/Library/Logs/shorts-pipeline}
domain="gui/$(id -u)"

mkdir -p "$agent_dir"
mkdir -p "$log_dir"
for plist in \
    com.shorts-pipeline.reddit-worker.plist \
    com.shorts-pipeline.github-monitor.plist \
    com.shorts-pipeline.youtube-analytics.plist \
    com.shorts-pipeline.analytics-sync.plist; do
    source="$repo_dir/scripts/$plist"
    target="$agent_dir/$plist"
    test -f "$source" || { echo "Missing launchd file: $source" >&2; exit 1; }
    plutil -lint "$source" >/dev/null || { echo "Invalid launchd plist: $source" >&2; exit 1; }
    cp "$source" "$target"
    label=$(basename "$plist" .plist)
    launchctl bootout "$domain/$label" 2>/dev/null || true
    if ! launchctl bootstrap "$domain" "$target"; then
        echo "Unable to register $label; plist was copied to $target" >&2
        exit 1
    fi
    if ! launchctl print "$domain/$label" >/dev/null 2>&1; then
        echo "Job was not visible after registration: $label" >&2
        exit 1
    fi
done

echo "Installed and registered Shorts Pipeline launchd jobs"
