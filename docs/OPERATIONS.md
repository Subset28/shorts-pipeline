# Operations

Start with `python -m shorts_pipeline run --dry-run`. Keep `DRY_RUN=true` until
the output and source citations are acceptable. Store OAuth tokens, client
secrets, and ElevenLabs `keys.json` outside Git.

TTS prefers the local ElevenLabs rotator when configured, then falls back to
the keyless `edge-tts` command using `EDGE_TTS_VOICE`.

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

For an always-on host, run `docker compose up -d --build`. The container
restarts after process failures and keeps `data/` and `output/` on the host.
Use `DRY_RUN=true` for the first deployment; switch it only after both platform
credentials have been tested with private uploads.

## Metrics feedback loop

Export platform analytics to a CSV with `source_url`, `platform`, and `views`
columns, plus optional `likes`, `comments`, and `shares`. Run:

```powershell
python -m shorts_pipeline report --metrics metrics.csv
```

The command writes `data/analytics_report.json` and groups matched videos by
category, format, and platform. It never fabricates view counts; unmatched
rows are reported separately for cleanup.
