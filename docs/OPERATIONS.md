# Operations

Start with `python -m shorts_pipeline run --dry-run`. Store OAuth tokens, client
secrets, and ElevenLabs `keys.json` outside Git.

TTS prefers the local ElevenLabs rotator when configured, then falls back to
the keyless `edge-tts` command using `EDGE_TTS_VOICE`.

To collect real professional anecdotes, configure Reddit OAuth credentials and
run `python -m shorts_pipeline reddit --count 10`. This writes candidates only;
the configured records in `REDDIT_APPROVED_FILE` are operator-confirmed and
eligible for the dedicated Reddit-story lane, whose default treatment uses
that lane directly.

Use the `split` command only for clips whose reuse rights are already cleared;
it creates independently playable 2–4-part files and does not publish them by
itself.

Captions are enabled by default. Install `pip install -e .[captions]` to use
local `faster-whisper` audio alignment; without it, the free fallback creates
timed captions from the generated narration. The first Whisper run may
download the selected model (`CAPTION_MODEL`, default `base`).

Each render manifest includes a quality report with duration sync, background
coverage, caption coverage, and any failed checks. Treat `quality.passed=false`
as a review gate before publishing.
For a no-media release check, use `python -m shorts_pipeline run --preflight`.
The `--dry-run` option is render-only and can still consume substantial CPU;
it skips uploads but is not a configuration check.
The unattended worker uses one selected Minecraft/background source by default
to limit CPU. `BACKGROUND_REEL_ENABLED=true` opts into multi-segment background
generation and should be enabled only after a host-specific resource check.

Every short and long-form render also creates `thumbnail.jpg` at 1280x720 and
records it in the manifest. YouTube uploads attempt to set that custom
thumbnail after the video upload; if thumbnail setup fails, the video ID is
kept so a retry cannot create a duplicate upload. Titles are capped at the
YouTube limit, descriptions retain readable paragraphs, and tags are cleaned,
deduplicated, and kept bounded. Treat these as packaging aids, not a reason to
stuff keywords or make claims the video does not support.

For source footage with multiple speakers, install WhisperX and set
`WHISPERX_DIARIZATION=true` plus a Hugging Face token (`HF_TOKEN`). The
pipeline then writes the same SRT timing alongside speaker-colored ASS
captions; if diarization is unavailable, it falls back to regular Whisper.

YouTube requires OAuth with `youtube.upload`; unverified API projects make
uploads private until audit. TikTok Direct Post requires an approved app and
the `video.publish` scope; unaudited clients are private-only. Use the
platform-specific privacy values returned by TikTok creator-info rather than
assuming public access.

TikTok processing is asynchronous. The pipeline persists the returned
`publish_id`, records the upload as processing, and checks the official status
endpoint on the next run. It marks the source seen only after
`PUBLISH_COMPLETE`; a reported failure stops the run instead of claiming a
successful post.

When variants are enabled, platform retry state is keyed by source plus
variant (`source_url#variant=N`); the default variant retains the legacy
source-only key. This prevents one treatment from reusing another treatment's
upload IDs.

For an always-on host, run `python -m shorts_pipeline run --daemon --reddit-only
--youtube-only --interval-hours 6` under a restartable supervisor. TikTok is
not invoked by `--youtube-only`.

Use `python -m shorts_pipeline schedule --file data/reddit_next_week_schedule.json`
for approved entries. YouTube requires scheduled uploads to use private status
with a future RFC 3339 `publishAt`; YouTube makes them public at that time.

Use `python -m shorts_pipeline plan-week --week-of YYYY-MM-DD` to create a
balanced weekly slate. It targets seven Shorts plus one long-form entry,
rotates categories when enough source-backed topics exist, writes private UTC
publish times, and only plans work. Render and inspect the entries before
using the separate schedule or long-form commands.

Before planning, use `python -m shorts_pipeline research-week --week-of
YYYY-MM-DD --out data/research_week.json` to create a private editorial brief
for each candidate. Review the source claim, URL, hook, format, visual
direction, metadata, long-form bridge, and rights gate. Then pass
`--research data/research_week.json` to `plan-week`; malformed research data
is rejected, and the plan remains private.

Run `python -m shorts_pipeline produce-week --plan data/weekly_plan.json` to
execute a reviewed slate. It is render-only by default, caps the slate at
seven Shorts plus one long-form entry, rejects non-private plans, and never
invokes TikTok. Add `--upload-private` only when private YouTube drafts are
intended.
The same flag uploads the reviewed long-form entry as a private YouTube draft
and preserves its planned publish time; long-form remains render-only without
the flag.
Each Short also receives its own planned publish time from the reviewed slate.
Run `produce-week --preflight` before production to validate the plan without
starting media generation or platform requests.
Uploads are blocked unless the manifest has valid source-linked metadata and
caption evidence; Shorts additionally need a selected background visual.
Failed metadata evidence raises an error before any platform request is made.
The Reddit worker launchd job uses background scheduling, low-priority I/O,
and a restart throttle to reduce load on the Mac during media generation.
FFmpeg also defaults to two worker threads with single-threaded filter graphs;
set `FFMPEG_THREADS` between 1 and 4 when tuning resource use on a host.
For weekly preparation, `python -m shorts_pipeline prepare-week` writes both
private planning artifacts from one discovery pass. It is planning-only;
`produce-week` remains the separate render/upload step.
Pass `--reddit-only` when the week must use only approved Reddit sources;
this bypasses general discovery and leaves the approval queue unchanged.
The generated plan is source-set checked against the research slate and keeps
one matching brief per scheduled entry.

On the configured Windows host, `.\scripts\deploy-nas.ps1` performs the
same deployment using the `synology` SSH alias. It uses legacy SCP for the
Synology SSH server, creates the project directories if needed, preserves an
existing remote `.env`, and never transfers local credentials.

## Metrics feedback loop

Export platform analytics to a CSV with `source_url`, `platform`, and `views`
columns, plus optional `variant`, `likes`, `comments`, and `shares`. Include
`variant` when comparing multiple treatments of one source; without it, rows
are matched only when that source has a single known treatment. Run:

```powershell
python -m shorts_pipeline report --metrics metrics.csv
```

The command writes `data/analytics_report.json` and groups matched videos by
category, format, and platform. It never fabricates view counts; unmatched
rows are reported separately for cleanup.

To create a Git-tracked, repository-safe snapshot, run
`python -m shorts_pipeline archive-analytics --input data/analytics_report.json
--week-of YYYY-MM-DD --out docs/analytics/YYYY-MM-DD.json`, then commit that
file. The archive contains aggregate lane rows, conservative recommendations,
and an `experiment_brief`. When at least two videos exist in two lanes, that
brief records measured baseline/reference lanes and turns CTR into a
title/thumbnail test and retention into an opening/pacing test. With fewer
than two videos per lane it records `insufficient_sample` and prescribes no
creative change.
The Sunday launchd job runs the SSH sync and opens a dedicated GitHub PR for
the same archive automatically when a new report exists.

The weekly analytics sync sends only an explicit allowlist of report artifacts
(`analytics_report.json`, `youtube_analytics.json`, `youtube_weekly_report.json`,
and `tuning_log.md`) to the
configured SSH target. It never sends `.env`, OAuth tokens, client secrets, or
API keys. Install `scripts/com.shorts-pipeline.analytics-sync.plist` with
launchd to run Sundays at 23:30; override `ANALYTICS_REMOTE_HOST` and
`ANALYTICS_REMOTE_DIR` when the Windows/NAS SSH alias or path differs.

With `--weekly`, the analytics command also converts the latest per-video
snapshots into `data/analytics_report.json`, which the next weekly planner
uses. Reach exports may use YouTube Reporting API field names such as
`video_thumbnail_impressions` and `video_thumbnail_impressions_ctr`; the
report normalizer accepts those names as well as Studio CSV aliases.

Install or refresh all Mac jobs with `scripts/install-launchd-jobs.sh`. The
installer copies each plist, registers it in the current user's launchd
domain, and stops with the copied file path if macOS rejects a job.
It also verifies each label is visible after registration; a successful install
therefore proves the analytics supervisor is loaded, not merely copied.

## Background library

Run `python -m shorts_pipeline backgrounds` on a new host to provision the
cataloged motion footage into `data/backgrounds`. Each entry records its source
page, attribution, and rights note in `assets/backgrounds.json`; do not add
uncataloged downloads to the publishing library.

When at least two cataloged assets are available, each render builds a silent
12-second reel from up to three sources with four-second cuts. The manifest
records both the generated reel and its source files.

User-provided background clips may be placed in `data/backgrounds` and are
selected automatically, but must be listed in `assets/user_backgrounds.json`.
Credit the original creator and include the original channel URL in the final
upload description after verifying the source license; attribution by itself
does not establish reuse permission.
