#!/bin/sh
set -eu

repo_dir=${PIPELINE_REPO_DIR:-/Volumes/n2me/Developer/shorts-pipeline}
runtime_data=${ANALYTICS_LOCAL_DIR:-/Users/abba/shorts-pipeline/data}
week_of=${1:-$(date -u +%F)}
branch="analytics/weekly-$week_of"
source_report="$runtime_data/youtube_weekly_report.json"
if [ ! -f "$source_report" ]; then
    source_report="$runtime_data/analytics_report.json"
fi
test -f "$source_report" || { echo "No analytics report to archive: $source_report" >&2; exit 0; }

worktree=$(mktemp -d "${TMPDIR:-/tmp}/shorts-analytics.XXXXXX")
cleanup() {
    git -C "$repo_dir" worktree remove --force "$worktree" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

git -C "$repo_dir" worktree add --detach "$worktree" origin/main >/dev/null
git -C "$worktree" switch -c "$branch" >/dev/null
mkdir -p "$worktree/docs/analytics"
/Users/abba/shorts-pipeline/.venv/bin/python -m shorts_pipeline archive-analytics \
    --input "$source_report" \
    --week-of "$week_of" \
    --out "$worktree/docs/analytics/$week_of.json"
git -C "$worktree" add "docs/analytics/$week_of.json"
if git -C "$worktree" diff --cached --quiet; then
    echo "Analytics archive already exists for $week_of"
    exit 0
fi
git -C "$worktree" commit -m "docs: archive analytics for $week_of" >/dev/null
git -C "$worktree" push origin "HEAD:refs/heads/$branch" >/dev/null
gh pr create --repo Subset28/shorts-pipeline --base main --head "$branch" \
    --title "docs: archive analytics for $week_of" \
    --body "Weekly aggregate analytics snapshot for $week_of. Contains lane metrics and tuning recommendations only; no raw events or credentials."
