# Shorts Pipeline

Source-backed production for entertainment-first technology stories. Signal
Forge can cover any technology by turning strong sources into tension,
escalation, visual proof, and payoff—not miniature lectures or automated Reddit
readings.

The governing creative contract is
[`docs/SHORTS_CREATIVE_SPEC_V2.md`](docs/SHORTS_CREATIVE_SPEC_V2.md). The staged
implementation is in
[`plans/shorts-v2-retention-engine.md`](plans/shorts-v2-retention-engine.md), and
[`docs/LOW_COST_AGENT_HANDOFF.md`](docs/LOW_COST_AGENT_HANDOFF.md) is the cold-start
runbook for cheaper coding models. Until the v2 blueprint is implemented, the
current renderer must not be represented as meeting the v2 creative gate.
The free/local tool and host layout is documented in
[`docs/PRODUCTION_STACK_V2.md`](docs/PRODUCTION_STACK_V2.md); competitor learning
and provider-compliant generated media are governed by
[`docs/COMPETITOR_RESEARCH_SPEC.md`](docs/COMPETITOR_RESEARCH_SPEC.md).
The broader autonomous-studio direction lives in
[`docs/CHANNEL_STRATEGY_V3.md`](docs/CHANNEL_STRATEGY_V3.md),
[`docs/STUDIO_CRAFT_STANDARD_V3.md`](docs/STUDIO_CRAFT_STANDARD_V3.md), and
[`plans/signal-forge-world-class-studio.md`](plans/signal-forge-world-class-studio.md).
Exact implementation schemas and autonomous release thresholds are in
[`docs/V2_DATA_CONTRACTS.md`](docs/V2_DATA_CONTRACTS.md) and
[`docs/V2_EVAL_RUBRIC.md`](docs/V2_EVAL_RUBRIC.md).

The pipeline discovers a topic, writes original cited metadata, renders a 9:16
MP4 with FFmpeg, adds narration, burns captions, and publishes through official
APIs.

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

Pixazo is an optional, disabled-by-default generated-shot provider. Configure one
authorized key plus a positive `PIXAZO_DAILY_REQUEST_LIMIT`, then inspect only
local configuration with `python -m shorts_pipeline pixazo-status`. It is a
bounded shot adapter, not a multi-account rotator; it must never be used to
evade provider quotas or replace source evidence with generated footage.

From Windows, repeat the Synology deployment with
`.\scripts\deploy-nas.ps1`. It uses the configured `synology` SSH alias,
legacy SCP compatibility, preserves an existing remote `.env`, and never copies
local credentials.

The visual defaults and footage/caption rules are documented in
`docs/STYLE_GUIDE.md`. Where older format guidance conflicts with the v2
creative specification, the v2 specification governs new work.

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
When `data/analytics_report.json` contains a ready experiment brief, planning
prefers the measured reference category while preserving rotation and records
the exact review target. Use `--analytics path/to/report.json` to select a
different report; incomplete samples do not alter the slate.

Create a reviewable, source-backed editorial slate first with
`python -m shorts_pipeline research-week --week-of YYYY-MM-DD`. It records the
source claim, evidence URL, hook, eligible format, visual direction, caption
plan, metadata, long-form bridge, and rights gate for each selected story. Add
`--research data/research_week.json` to `plan-week` to attach those briefs to
the private weekly plan. Research and planning never render or publish.
When `produce-week` consumes that plan, the validated brief shapes the
Short's hook and metadata plus the long-form question, chapters, and packaging
before narration/rendering; a mismatched or public brief is rejected.
If `research-week` finds a ready analytics experiment in
`data/analytics_report.json`, it records a concrete hook or packaging treatment
in the private brief for the next controlled test.

Execute a reviewed plan with `python -m shorts_pipeline produce-week --plan
data/weekly_plan.json`. It renders only by default. Add `--upload-private` to
upload Shorts as private YouTube drafts; the command never publishes publicly
or invokes TikTok.
With `--upload-private`, the long-form entry is also uploaded as a private
YouTube draft and keeps its planned publish time.
Shorts likewise keep their individual planned publish times from the weekly
plan.
Before any upload, the manifest must pass both render-quality and
source-linked metadata gates; Shorts also require a background visual and all
uploads require captions.
Run `produce-week --preflight --plan data/weekly_plan.json` to validate the
slate without TTS, rendering, or uploads.
Either gate blocks the upload when it fails.
The unattended Reddit launchd job is configured as background/low-priority and
throttled after exit to reduce host resource contention.
Long-form renders include an original technical flow visual alongside the
title card, captions, and selected background.
Use `python -m shorts_pipeline prepare-week --week-of YYYY-MM-DD` to create
the private research slate and scheduled production plan in one discovery
pass; it never renders or publishes.
Use `--reddit-only` to build the slate exclusively from the approved Reddit
queue, without changing permission records.
Use `run --preflight` to validate local credentials, backgrounds, and TTS
configuration without starting TTS, FFmpeg, or an upload. `run --dry-run`
still renders media and only skips platform uploads.
Unattended runs use one selected moving background by default; set
`BACKGROUND_REEL_ENABLED=true` only after benchmarking the host to enable the
more expensive multi-segment reel.
The plan is constrained to the same source set as the research slate, so every
scheduled entry retains its matching editorial brief.

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
The scheduled `analytics --weekly` path also writes the planner-facing
`data/analytics_report.json`. It uses a persisted YouTube Reporting API Reach
Basic job for thumbnail impressions and CTR; the job ID is stored in ignored
data, never in source control.
