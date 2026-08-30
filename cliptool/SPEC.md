# cliptool — Twitch/YouTube bounded-clip scout & extractor

**Status:** v1 implemented
**Date:** 2026-08-26

## Problem

Given a Twitch or YouTube channel/video/VOD/clip URL, produce a list of
*bounded* 8-90s candidate segments (not whole videos), each with enough
metadata to immediately: fetch/download it, score/rank it, write a hook,
and hand it to a render pipeline.

## Scope

- Input: Twitch channel / VOD / clip URL, YouTube channel / video URL.
- Output: `candidates.json` — a list of `Candidate` objects (schema below).
- `cliptool fetch` downloads one candidate's exact bounded segment
  (`yt-dlp --download-sections`), optionally grabs 1-3 preview frames.
- A local FastAPI service exposes the same scout/fetch actions plus
  config read/write, so other agents can drive this tool over HTTP.
- Out of scope: ranking/selection into `selected_for_render.json` —
  that's a downstream step. `candidates.json` uses the *same* schema as
  `selected_for_render.json`, so selection is just filtering a list.

## Candidate schema

```json
{
  "source_id": "yt:VIDEOID:145-210",
  "platform": "youtube | twitch_clip | twitch_vod",
  "candidate_kind": "youtube_window | twitch_clip | twitch_vod_window",
  "creator_name": "string",
  "video_url": "string (playable url for this segment's parent video)",
  "original_source_url": "string | null (the URL the user originally gave, if different)",
  "start_seconds": 145,
  "end_seconds": 210,
  "duration_seconds": 65,
  "title": "string",
  "why_selected": "string (human-readable reason/score breakdown)",
  "transcript_excerpt": "string | null",
  "preview_frames": ["path/or/url", "..."],
  "thumbnail_url": "string | null",
  "view_count": 12345,
  "clip_view_count": 12345,
  "game_or_topic": "string | null",
  "license_or_rights_note": "string | null",
  "reuse_risk_note": "string | null",
  "safety_notes": ["age_restricted: false", "flagged_terms: none"],
  "score": 0.82,
  "published_at": "ISO8601 string | null",
  "acquisition_status": "pending | acquired | blocked | partial",
  "acquisition_detail": "string | null"
}
```

## Platform behavior

- **Twitch clips**: already bounded by the creator. No windowing —
  pass Helix clip metadata straight through as one `Candidate`.
- **YouTube videos**: pull transcript (`youtube-transcript-api`, free,
  no quota cost), slide an 8-90s window across it, score windows on a
  weighted mix of: transcript keyword density, transcript density
  spikes, title keyword match, punctuation/excitement markers, short
  duration preference, recency, popularity (view count). Return
  non-overlapping top-N windows (respects `min_gap_between_selected_windows`).
  If no transcript is available, fall back to fixed-interval chunking
  (same as Twitch VOD fallback) and note the lower confidence.
- **Twitch VODs**: rarely have captions. v1 uses fixed-interval
  chunking (`vod_chunk_seconds`) as a low-confidence fallback;
  `why_selected` and `safety_notes` explicitly flag this as
  low-confidence until chat/transcript/event signals are wired in.

## Config (`config.json`, API-editable)

Editable: `min_clip_seconds`, `max_clip_seconds`,
`max_candidates_per_source`, `twitch_clip_window_days`,
`youtube_search_limit`, `vod_chunk_seconds`,
`min_gap_between_selected_windows`, `language_allowlist`,
`excluded_terms`, `include_shorts`, `youtube_daily_quota_cap`,
`scoring_weights.*`, `safety.*`, `platforms_enabled.*`.

Never editable via API: secrets. `TWITCH_CLIENT_ID`,
`TWITCH_CLIENT_SECRET`, `YOUTUBE_API_KEY` live only in `.env`
(gitignored). The API exposes booleans (`"twitch_configured": true`)
never the raw values, and has no endpoint that accepts a secret value.

## Quota

YouTube Data API v3 free tier = 10,000 units/day. `quota.py` tracks
daily usage in `cache/youtube_quota.json` and refuses further YouTube
calls once `youtube_daily_quota_cap` is hit (default 9000, leaving
headroom). `search.list` (100 units) is avoided where a cheaper
`channels.list`/`videos.list` (1 unit) call suffices.

## API

Local-only (binds 127.0.0.1), no auth (nothing sensitive is exposed):

- `GET /health`
- `GET /config`
- `PUT /config` — partial update, validated (rejects unknown keys,
  enforces `min < max`, etc.)
- `GET /config/schema`
- `POST /scout` — body: `{source, min, max, out}` → runs the same
  logic as `cliptool scout`, returns candidates inline and writes the
  file.
- `POST /fetch` — body: `{candidates_file, candidate_id, out}` → runs
  the same logic as `cliptool fetch`.

## Error handling

- Bad/unrecognized URL → CLI exits nonzero with a clear message;
  nothing written.
- YouTube quota near cap → refuse further YouTube calls, return
  partial results with a warning, don't crash.
- No transcript → auto fallback to fixed-interval windowing, noted in
  `why_selected`.
- yt-dlp failure (deleted/private/age-gated) → that candidate's
  `acquisition_status` becomes `blocked` with `acquisition_detail` set;
  batch continues.
- Twitch Helix pagination handled transparently.

## Testing

Pure-function unit tests for windowing/scoring against fixture
transcripts (no network). FastAPI `TestClient` tests for the config
API. No live network calls in the test suite — protects YouTube quota.

## Directory layout

```
projects/cliptool/
  README.md
  SPEC.md
  requirements.txt
  .env.example
  config.json
  .gitignore
  cliptool/
    cli.py
    config.py
    models.py
    quota.py
    safety.py
    transcript.py
    extractor.py
    url_parse.py
    platforms/{twitch.py, youtube.py}
    scout/{windowing.py, clips.py}
  api/app.py
  launchd/com.cliptool.api.plist.example  # persistent-service template for the Mac mini
  tests/{test_windowing.py, test_config_api.py, fixtures/}
  outputs/   # fetched clips + frames land here (gitignored contents)
  cache/     # quota counter, transcript cache (gitignored contents)
```
