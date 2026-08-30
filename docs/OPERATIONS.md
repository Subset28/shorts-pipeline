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
