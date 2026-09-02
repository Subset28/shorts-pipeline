# Signal Forge v2 production stack

Status: approved target architecture. Installation and activation happen through
the PR sequence in `plans/shorts-v2-retention-engine.md`, not ad hoc on `main`.

Goal: produce premium 1080x1920 technology Shorts with free/local tools, using
the Mac mini for orchestration and bounded rendering, N2ME for active media, and
the DS1019+ for durable storage, proxies, and archives.

## 1. Stack principles

- Free/local is a cost boundary, not a quality excuse.
- One tool owns each job. Avoid duplicate renderers and glue layers.
- Every executable and model is version-pinned after a supervised benchmark.
- Every asset and model has a license/provenance record before production use.
- Preview quality and release quality are separate states.
- A tool is not adopted because it can render a demo. It must pass visual,
  deterministic-output, resource, and cold-start-agent tests.

## 2. Selected tools

| Job | Target tool | Why | Release condition |
| --- | --- | --- | --- |
| Master 9:16 composition | Remotion + React + TypeScript | Typed, frame-driven scenes, exact sequencing, dynamic duration, measured text, captions, audio, and reusable motion components | Confirm current license fits the operator; pin version; render golden fixtures |
| Precise technical animation | Manim Community | Programmatic graphs, architecture diagrams, counters, equations, and transformations | Isolated environment; export transparent or keyed clips |
| 3D/VFX hero shots | Blender LTS | Product-scale macro shots, network spaces, particles, camera moves, lighting, and compositing | Use official stable/LTS build and scripted, reproducible scenes |
| Editorial interchange | OpenTimelineIO | Inspectable timeline containing clips, tracks, transitions, markers, and metadata without embedding media | Keep OTIO as the canonical edit decision artifact |
| Final encode/probe/mix | FFmpeg/ffprobe | Existing deterministic encode, loudness, mux, thumbnail, and verification layer | Codec-level threads and host resource profile enforced |
| Caption alignment | local OpenAI Whisper or faster-whisper | Word timing and local operation without a hosted API | Model cached on N2ME; resource benchmark; no silent text-timing fallback for public masters |
| Local voice candidate | Kokoro-82M benchmark | Small local neural TTS candidate with a permissive base-model license | Voicepack provenance plus automated pronunciation, emotion, and reference-quality tests must pass; otherwise use ElevenLabs or a preapproved recorded voice |
| Cleared media acquisition | yt-dlp adapter | Reliable download of explicitly permissioned source media | URL, owner, permission, use scope, checksum, and attribution recorded first |
| Optional generated shot | provider-compliant Higgsfield adapter or another approved free plan | Fill a visual gap when real evidence or local animation cannot create the shot | One authorized account, official quota, cached outputs, generation manifest, and local fallback |
| Sound editing | FFmpeg filters; Audacity only for exceptional debugging | Free phrase edits, loudness, ducking, and layered mix generation | Export stems and automated final mix report |
| Release arbiter | local multimodal model through a pinned Ollama/MLX-compatible runtime plus deterministic validators | Unattended visual/transcript critique without a hosted API | Benchmark model/license, require cited frame evidence, and fail closed |
| Asset index | SQLite manifest + checksums | Fast local search with durable provenance and duplicate detection | Database rebuildable from sidecar manifests |

Remotion is free for individuals under its current hybrid terms; a company use
case must re-check its license before activation. Manim Community is MIT-licensed.
Blender is GPL software and its official license page states that artwork created
with it remains the creator's property. OpenTimelineIO uses an Apache-2.0 license.
Local OpenAI Whisper code is MIT-licensed. Model weights, voicepacks, fonts,
templates, plugins, footage, music, and sound effects still require their own
records.

Primary references, checked 2026-09-02:

- https://www.remotion.dev/
- https://docs.manim.community/en/stable/
- https://www.blender.org/about/license/
- https://opentimelineio.readthedocs.io/en/latest/
- https://github.com/openai/whisper/blob/main/LICENSE
- https://github.com/hexgrad/kokoro

## 3. What is removed from public production

- Minecraft or generic gameplay backgrounds.
- macOS `say`, edge-TTS, or untouched utility narration.
- static Pillow story cards as the main composition.
- one looping background behind an entire story.
- auto-generated diagrams that do not correspond to a source-backed mechanism.
- generic “AI” stock imagery, fake terminals, random code, and glowing-brain art.
- uncataloged YouTube downloads, music, sound effects, fonts, models, or plugins.
- free-tier account rotators, account farms, quota evasion, or identity spoofing.

These may exist in clearly labeled engineering fixtures where needed. The public
upload gate rejects them.

## 4. Host topology

```text
Reddit/API/permissioned source media
              |
              v
Mac mini control plane
  - source research and scoring
  - beat sheet and visual plan
  - Remotion Studio/debug UI
  - Manim/Blender asset jobs, one at a time
  - local voice/caption jobs, one at a time
  - preview render and quality gates
  - upload/analytics/launchd supervisors
              |
              v
N2ME active workspace
  - repositories and environments
  - current source media and proxies
  - render cache and current batch
  - models required by active jobs
              |
              v
DS1019+ durable media plane
  - approved source library
  - immutable originals and checksums
  - proxies and generated reusable assets
  - project bundles and final masters
  - analytics archives and backups
```

The NAS is not the primary renderer. Its role is capacity, durability, sharing,
and recovery. Active frame caches remain on N2ME to avoid network latency.

## 5. Directory contract

### N2ME active workspace

```text
/Volumes/N2ME/Developer/shorts-pipeline/
  video/                       Remotion source and tests
  motion/manim/                Manim scenes
  motion/blender/              Blender templates and scripts
  data/assets/index.sqlite     rebuildable local asset index
  data/assets/active/          current source assets
  data/assets/proxies/         current editing proxies
  data/models/                 pinned active local models
  output/previews/             watermarked engineering previews
  output/masters/              gated 1080x1920 masters
  output/review/               contact sheets and arbiter packets
  output/logs/                 bounded job logs
```

### DS1019+ durable layout

```text
/volume1/signal-forge/
  originals/                   immutable permissioned media
  manifests/                   source, rights, checksums, attribution
  proxies/                     reusable edit proxies
  generated/manim/             approved reusable animations
  generated/blender/           approved reusable hero shots
  audio/voice/                 approved voice takes and pronunciation maps
  audio/music/                 cleared beds and licenses
  audio/sfx/                   cleared effects and licenses
  projects/YYYY-WW/<story-id>/ OTIO, props, scripts, arbiter records
  masters/YYYY-WW/             final masters and upload metadata
  analytics/                   Git-safe weekly exports
  backups/                     repository and manifest backups, never secrets
```

No `.env`, OAuth token, client secret, API key, or private voice credential is
copied to the NAS.

## 6. Asset manifest contract

Every external asset has:

```json
{
  "asset_id": "sha256-prefix",
  "type": "video|image|audio|font|model|plugin",
  "original_url": "https://...",
  "creator": "...",
  "permission_basis": "written_permission|public_domain|license",
  "license_id": "...",
  "allowed_use": ["youtube_short", "derivative", "commercial"],
  "attribution": "...",
  "approved_by": "release-arbiter version or explicit operator override",
  "approved_at": "RFC3339",
  "sha256": "...",
  "local_original": "nas-relative path",
  "proxy": "optional n2me-relative path"
}
```

Missing or ambiguous fields block production. Attribution alone is not
permission.

## 7. Render states

1. **Storyboard** — still frames and temporary voice; no platform use.
2. **Preview** — 720x1280 watermarked render; utility voice and temporary assets
   allowed; public upload impossible.
3. **Arbiter candidate** — complete 1080x1920 composition, final voice and mix,
   source/provenance complete; no upload until automated evaluation.
4. **Master approved** — all technical, creative, rights, transcript, visual,
   and independent-arbiter gates pass; immutable checksum recorded.
5. **Platform derivative** — upload copy and metadata derived from the approved
   master without changing editorial content.

State transitions are one-way and logged. Replacing any media, narration, timing,
or metadata after approval creates a new arbiter candidate.

## 8. Remotion composition contract

- One typed JSON props file per story, generated from the beat sheet and visual
  plan.
- `calculateMetadata` derives duration from narration and scene timing.
- All animations use frame values; CSS animations and transitions are forbidden.
- Every sequence is premounted.
- Text uses loaded local fonts and measured fit; overflow is a hard failure.
- Captions use word timing and current-word emphasis, not a permanent giant block.
- Transitions overlap intentionally and their frame cost is included in duration.
- Audio has separate voice, bed, ambience, and effect tracks.
- A deterministic seed controls any particles, noise, or procedural layout.
- A golden-frame test covers the first frame, promise, mechanism, and payoff.

## 9. Free local voice benchmark

Do not install five TTS systems. Benchmark one small candidate first.

Test script includes:

- fast tension;
- restrained explanation;
- disbelief;
- a technical acronym and product name;
- a number contrast;
- a quiet beat before payoff.

Benchmark Kokoro against the best existing ElevenLabs reference take and a
preapproved reference-voice set. Measure back-transcription error, pronunciation
exceptions, pace, silence, loudness, spectral artifacts, and an independent
audio-critic score for naturalness, emotion, fatigue, and editability. The local
model becomes public-eligible only if its selected voicepack has clear
commercial/derivative rights and meets the automated quality floor. Otherwise
it remains a preview tool.

## 9.1 Autonomous release service

The Mac mini hosts one local release-arbiter job. It consumes only derived review
media and metadata, not credentials. Its checks are:

- deterministic rights, asset, render, caption, loudness, silence, and text-fit
  validation;
- Whisper back-transcription against approved narration;
- OCR and caption-collision detection;
- perceptual-hash detection of repeated or placeholder shots;
- multimodal scoring of frame one, promise, escalation, mechanism, payoff, and
  random-frame polish;
- evidence verification requiring timestamps or frame IDs for every pass;
- at most two targeted revisions before the source is held.

The producing model cannot approve its own video. The release arbiter uses a
separate prompt, version, cache, and report. Posting is the only optional human
action.

## 10. Mac mini services

Use separate restartable launchd jobs with low priority and non-overlapping locks:

- `research-refresh`: candidate discovery only;
- `asset-index`: checksum/provenance/proxy updates;
- `render-preview`: one Remotion preview job;
- `render-master`: one 1080 master job with resource monitor;
- `analytics-snapshot`: 24-hour and weekly metrics;
- `nas-sync`: approved allowlist only;
- `github-monitor`: PR/review/push notifications.

Each job has a hard timeout, explicit N2ME working directory, host-resource log,
and retry delay. A failed creative or rights gate is terminal until source data
changes; a transient network or render-host failure is retryable.

## 11. NAS workflow

- Ingest only through a manifest-aware command.
- Copy originals once, verify checksum, then make them read-only to the worker.
- Generate lightweight proxies for editing; never repeatedly decode a huge NAS
  original for previews.
- Sync approved masters and project bundles after the arbiter passes.
- Keep at least one independent backup of manifests and masters; RAID is not a
  backup.
- Weekly Windows/NAS sync transfers only allowlisted analytics and production
  artifacts, never credentials.

## 12. Adoption order

1. Add license/asset registry and host health checks.
2. Scaffold Remotion with one golden composition and no platform integration.
3. Add Manim mechanism exports.
4. Benchmark Kokoro and caption alignment locally.
5. Build one source-specific episode end to end.
6. Validate 720 preview on Mac, then bounded 1080 master.
7. Add NAS project bundle and recovery test.
8. Only then connect the creative gate to private-draft upload.

No tool is installed merely because it appears in this document. Each adoption
step is a reviewed PR with version pin, license record, health check, focused
test, uninstall/rollback notes, and measured resource impact.
