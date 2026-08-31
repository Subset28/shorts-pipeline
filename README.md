# Shorts Pipeline

Source-backed, unattended short-form publishing for YouTube Shorts and TikTok.
The pipeline discovers a topic, writes original cited metadata, renders a 9:16
MP4 with FFmpeg, adds ElevenLabs narration through the local rotating-key helper,
burns captions from optional local faster-whisper, and publishes through official APIs.

It defaults to `DRY_RUN=true` and private uploads. The configured confirmed
Reddit queue may publish publicly to YouTube only. No scraped clips or
copyrighted music are used. See `docs/ARCHITECTURE.md` and `docs/OPERATIONS.md`.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
python -m shorts_pipeline run --dry-run
```

Required tools: `ffmpeg` and `ffprobe`. Install `faster-whisper` with
`pip install -e .[captions]` for audio-aligned local transcription; otherwise
the pipeline uses free text-timed captions. Real publishing requires OAuth
credentials for YouTube and TikTok plus approved posting scopes.

For unattended operation, use `python -m shorts_pipeline run --daemon` with a
process supervisor. The default free mode uses RSS, fallback copy, Pillow,
FFmpeg, and free edge-tts narration. An OpenAI API key and ElevenLabs rotator are optional quality upgrades;
a ChatGPT Plus subscription is not an API credential.

The included `Dockerfile` and `docker-compose.yml` provide a restart-on-failure
runtime for a NAS or other always-on host. Keep `.env` and the mounted `secrets`
directory local and private.

From Windows, repeat the Synology deployment with
`.\scripts\deploy-nas.ps1`. It uses the configured `synology` SSH alias,
legacy SCP compatibility, preserves an existing remote `.env`, and never copies
local credentials.

The visual defaults and footage/caption rules are documented in
`docs/STYLE_GUIDE.md`.

For a rights-cleared local clip, create bounded series parts with
`python -m shorts_pipeline split --input path\to\clip.mp4 --parts 4`.

Generate a queue of distinct drafts with `python -m shorts_pipeline batch
--count 3 --dry-run`; each asset is written to its own `output/batch-NN`
folder (with `item-NN` children; reruns allocate a new batch) and uses the
source/format telemetry path.

Collect candidate first-person industry stories through Reddit's official API
with `python -m shorts_pipeline reddit --count 10`. Candidates are written to
`data/reddit_candidates.json`; the configured queue contains operator-confirmed
reuse permission. Configure `REDDIT_APPROVED_FILE` to feed confirmed stories
into normal runs.

For controlled experiments, add `--variants 2` (or another small number) to
generate multiple treatments per source. Each manifest and telemetry event
records the variant so platform exports can be compared without losing the
source/category relationship.

Schedule approved Reddit stories with `python -m shorts_pipeline schedule
--file data/reddit_next_week_schedule.json`. Scheduled YouTube uploads remain
private until their RFC 3339 `publish_at` time and never invoke TikTok.

Build a balanced weekly slate with seven Shorts and one long-form slot using
`python -m shorts_pipeline plan-week --week-of YYYY-MM-DD`. The command writes
source URLs, categories, private status, and UTC publish times to
`data/weekly_plan.json`; it plans only and never uploads or publishes.

Execute a reviewed plan with `python -m shorts_pipeline produce-week --plan
data/weekly_plan.json`. It renders only by default. Add `--upload-private` to
upload Shorts as private YouTube drafts; the command never publishes publicly
or invokes TikTok.

Provision the tracked, rights-documented background library with
`python -m shorts_pipeline backgrounds`. The command downloads only URLs in
`assets/backgrounds.json` and skips files already present.
Set `BACKGROUND_MANIFEST` when the local footage directory uses a different
asset manifest; category-aware selection will prefer matching footage when
the manifest supplies categories.

After publishing, export platform metrics to a CSV containing `source_url`,
`platform`, and `views` (optionally `variant`, `likes`, `comments`, and `shares`), then
run `python -m shorts_pipeline report --metrics metrics.csv`. The report joins
metrics to category/format telemetry so future batches can follow evidence.
