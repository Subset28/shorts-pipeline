#!/bin/sh
set -eu

/Volumes/n2me/Developer/shorts-pipeline/scripts/sync-analytics.sh
/Volumes/n2me/Developer/shorts-pipeline/scripts/archive-analytics-pr.sh "$@"
