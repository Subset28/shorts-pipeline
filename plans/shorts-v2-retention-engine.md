# Shorts v2 retention engine construction plan

Objective: replace explainer-first Reddit videos with an entertainment-first,
source-backed production system that reliably creates stronger hooks,
escalation, visual proof, payoffs, and measurable experiments.

Governing contracts: `docs/SHORTS_CREATIVE_SPEC_V2.md`,
`docs/V2_DATA_CONTRACTS.md`, and `docs/V2_EVAL_RUBRIC.md`. The contracts govern
whenever this blueprint is less specific; implementation models may not relax
them.

## Invariants for every PR

- Permission, attribution, source URL, and fact boundaries remain hard gates.
- TikTok remains off.
- Implementation and CI never upload publicly.
- Runtime media stays on N2ME.
- One FFmpeg job at a time; supervised smoke renders use 720x1280 and one thread.
- Minecraft is public-eligible only as polished kinetic support for the Reddit
  lane. macOS TTS, edge-TTS, and static Pillow cards remain preview-only.
- Public v2 masters are 1080x1920, use an approved performed voice, and require
  a passing autonomous release-arbiter state.
- Existing tests remain green; new behavior begins with focused tests.
- Every PR updates `PROJECT_STATUS.md` and reports creative, resource, and
  publishing impact.

## Dependency graph

```text
PR 0 Competitor intelligence
  -> demand evidence available to PR 1 and PR 8

PR 1 Story admission model
 ├── PR 2 Beat-sheet compiler
 │    ├── PR 4 Retention renderer
 │    └── PR 5 Audio/caption rhythm
 └── PR 3 Proof-asset planner
      └── PR 4 Retention renderer

PR 2 + PR 3 + PR 4 + PR 5
 └── PR 6 Creative quality gate and review packet
      ├── PR 7 Analytics treatment model
      └── PR 8 Bounded batch rollout
```

PRs 3 and 5 may run in parallel after their dependencies. All other order is
serial unless the plan is formally mutated.

## PR 0 — Competitor and format intelligence

Model tier: default/cheap for metadata and extraction; strongest available only
to calibrate the first pattern taxonomy.

Context: the current system learns mostly from its own small analytics sample.
It needs a lawful, non-copying view of topics, openings, durations, and visual
patterns that repeatedly outperform a channel's own baseline.

Primary files: new `shorts_pipeline/competitor_research.py`, YouTube metadata
adapter, research schemas, CLI, tests, `docs/COMPETITOR_RESEARCH_SPEC.md`.

Tasks:

1. Maintain a 10–20-channel cohort and fetch public metadata through official or
   authorized interfaces.
2. Calculate age-normalized view velocity and channel-outlier ratios.
3. Create temporary low-resolution analysis proxies and extract abstract hook,
   timing, shot, caption, and payoff features. Competitor media never enters the
   production library.
4. Require repeated evidence from at least three independent channels before
   flagging a pattern.
5. Write a Git-safe weekly packet with no cookies, tokens, downloaded media, or
   private competitor data.
6. Add an optional provider-compliant AI-video adapter interface. Explicitly
   prohibit account rotation and quota evasion; cache results and fall back to
   local tools.

Verification: fixed metadata fixtures, outlier math, missing-data behavior,
copyright-library separation, secret scanning, and deterministic packet output.

Exit criteria: the system can rank patterns without copying expression, can
explain every score, and continues safely when APIs or generation quota are
unavailable.

Rollback: disable competitor packets; source admission continues independently.

## PR 1 — Story admission model

Model tier: strongest available for scoring-contract design; cheaper model for
fixtures and implementation.

Context: current discovery rewards technical mechanisms and closure but does not
represent the creative admission score in the v2 spec. Weak advice and discussion
posts still consume editorial attention.

Primary files: `shorts_pipeline/models.py`, `shorts_pipeline/reddit.py`,
`shorts_pipeline/editorial.py`, `tests/test_pipeline.py`,
`tests/test_editorial.py`.

Tasks:

1. Add an immutable `StoryScore` record with all eight dimensions, total,
   evidence strings, rejection reasons, and a spec version.
2. Implement deterministic source-derived scoring. No LLM is required to admit
   or reject a story.
3. Make missing permission, missing closure, unverifiable central claim,
   promotion, and open advice automatic rejects.
4. Persist the score and lane in research briefs without changing raw discovery
   records.
5. Make weekly selection require 70+ and prioritize 80+ while retaining category
   balance among eligible stories.

Verification:

```bash
python -m pytest -q tests/test_pipeline.py -k 'reddit or story_score'
python -m pytest -q tests/test_editorial.py
python -m pytest -q
git diff --check
```

Exit criteria: fixtures explain every point and rejection; weak popularity cannot
beat an admitted story; existing permission gates remain intact.

Rollback: remove the score from selection while retaining it as research-only
metadata.

## PR 2 — Beat-sheet compiler

Model tier: strongest available for the first implementation; cheaper models can
extend fixtures.

Dependency: PR 1. PR 0 demand evidence may order admitted stories but cannot
change admission.

Context: `ScriptPackage` stores prose, but the v2 renderer needs explicit beats.
Narration and visuals must be generated from one progression rather than composed
independently.

Primary files: `shorts_pipeline/models.py`, `shorts_pipeline/seo.py`,
`shorts_pipeline/editorial.py`, `tests/test_pipeline.py`.

Tasks:

1. Add immutable `StoryBeat` fields: role, start target, narration, proof claim,
   visual intent, emphasis words, source attribution, and transition.
2. Compile admitted stories into cold-open, promise, setup, escalation, mechanism,
   payoff, and echo beats.
3. Enforce 75–110 words by removing explanation, never by deleting the payoff.
4. Block repeated claims and generic transition phrases.
5. Preserve complete source attribution in metadata while keeping it out of the
   first spoken line.

Verification: unit tests for all six lanes, word limits, claim uniqueness,
closure preservation, and attributed first-person claims.

Exit criteria: every eligible package has seven ordered beats; every sentence
belongs to one beat; the payoff is source-backed and present.

Rollback: serialize beats back to the current narration path without enabling
the new renderer.

## PR 3 — Proof-asset planner

Model tier: default/cheap.

Dependency: PR 1. May run in parallel with PR 2 if it does not edit shared model
types; otherwise wait for PR 2.

Context: background footage currently carries too much visual weight. V2 requires
source-specific receipts and honest original mechanism visuals.

Primary files: `shorts_pipeline/asset_library.py`, `shorts_pipeline/media.py`,
new `shorts_pipeline/visual_plan.py`, asset manifests, focused tests.

Tasks:

1. Define a `VisualAsset` manifest record containing source, permission,
   provenance, asset type, allowed uses, and optional attribution.
2. Map each beat to one proof asset, original generated visual, or explicitly
   labeled kinetic background.
3. Add deterministic visual-plan validation: first-frame artifact, six states,
   two proof visuals when available, no generic footage masquerading as evidence.
4. Add original templates for number contrast, system dependency, timeline,
   before/after, and mechanism flow.
5. Generate a reviewable JSON packet; do not download or render in this PR.

Exit criteria: every visual has provenance; invalid permission blocks selection;
the planner can explain why a beat has no proof asset.

Rollback: retain generated plans as research artifacts without feeding render.

## PR 4 — Retention renderer

Model tier: strongest available; renderer changes are high risk.

Dependencies: PR 2 and PR 3.

Context: current composition uses a long-lived Reddit card plus background and
captions. V2 needs beat-driven scenes, receipt flashes, proof objects, original
diagrams, and bounded pattern changes.

Primary files: new `video/` Remotion workspace, a bounded Python render adapter,
`shorts_pipeline/render.py`, `shorts_pipeline/resources.py`,
`shorts_pipeline/quality.py`, TypeScript and Python render tests.

Tasks:

1. Build a typed Remotion composition whose duration and props come from the
   beat sheet, narration timing, and visual plan.
2. Drive every animation from frames, use premounted sequences, measure all text,
   and use managed image/video/audio components so assets are ready before render.
3. Render development previews locally at 720x1280. Render 1080x1920 public
   masters through a bounded one-job queue, with an SSH Windows worker as the
   preferred fallback when the Mac cannot stay below its memory ceiling.
4. Render beat groups separately when required to cap memory, then concatenate
   and perform one bounded audio mux.
5. Use the Reddit card as a 0.8–2.0 second receipt after the cold open.
6. Add beat-specific compositions and motivated transitions with eight or more
   intentional shots.
7. Enforce codec-level thread limits and preserve renderer/FFmpeg diagnostics.
8. Add quality evidence for visual-state count, maximum static hold, receipt
   duration, first-frame artifact, and host profile.

Verification: command-level tests first; one supervised 20-second smoke; one
full-duration dry-run only after RSS remains below 750 MB.

Exit criteria: 720 preview and 1080 master both pass technical and visual gates;
audio delta <=100 ms; complete captions; no text overflow; RSS evidence recorded;
no upload; random-frame contact sheet has no placeholder or debug-looking frame.

Rollback: feature flag `RETENTION_RENDERER_V2=false` selects the current bounded
renderer.

## PR 5 — Audio and caption rhythm

Model tier: default/cheap.

Dependency: PR 2. May run in parallel with PR 3.

Context: timed captions and flat TTS can make a good story feel synthetic. This
PR improves pacing without requiring paid services.

Primary files: `shorts_pipeline/tts.py`, `shorts_pipeline/captions.py`, package
models, focused tests.

Tasks:

1. Add beat-aware performance direction, pause, and emphasis fields. Preview
   providers may degrade cleanly; public masters may not.
2. Normalize silence and reject pauses over 350 ms outside marked reveals.
3. Generate 2–5-word caption bursts with one emphasized word and collision-safe
   placement metadata.
4. Add pronunciation overrides for source-specific technical terms.
5. Add rights-cleared sound beds and beat-event cues with deterministic ducking,
   -14 to -16 LUFS target, and <= -1 dBTP true peak.
6. Add a public-release provider gate that rejects macOS and edge utility voices.

Exit criteria: no caption extends past audio; all words are covered; marked
reveals preserve intentional pauses; no provider fallback activates silently;
public manifests prove an approved voice and mix targets.

Rollback: ignore rhythm hints and use existing narration/caption generation.

## PR 6 — Autonomous creative quality gate and release arbiter

Model tier: default/cheap.

Dependencies: PRs 2–5.

Context: render-quality checks do not prove a Short has a promise, escalation,
payoff, or adequate visual density.

Primary files: new `shorts_pipeline/creative_quality.py`,
`shorts_pipeline/publish.py`, CLI, tests.

Tasks:

1. Implement deterministic checks from section 12 of the creative spec.
2. Write `creative_report.json`, a contact sheet, opening/payoff clips, OCR
   report, transcript comparison, and local multimodal-critic input packet.
3. Block upload when required structured evidence is missing.
4. Add an independent local multimodal critic whose ratings must cite observable
   frames, timestamps, or transcript lines.
5. Add a deterministic verifier for critic evidence and forbid the producer's
   own creative score from satisfying release.
6. Add bounded targeted regeneration: at most two revisions, then hold the
   source and continue the queue.
7. Add `review-short --manifest ...` to print the autonomous pass/fail packet
   without rendering or uploading.

Exit criteria: technical pass cannot override creative failure; the manifest
records spec version, arbiter version, critic evidence, and revision count;
dry-run fixtures cover each failure; no human action is required.

Rollback: run the gate in report-only mode while preserving evidence.

## PR 7 — Analytics treatment model

Model tier: default/cheap.

Dependency: PR 6.

Context: current analytics groups broad categories and formats. V2 needs to join
performance to creative variables.

Primary files: `shorts_pipeline/analytics.py`,
`shorts_pipeline/analytics_schedule.py`, reporting normalization, tests.

Tasks:

1. Persist story score, lane, duration, opening type, visual-state count, receipt
   timing, narration provider, and treatment ID with upload events.
2. Snapshot 24-hour and seven-day metrics.
3. Add retention checkpoints at 1/3/5/10/20 seconds when the API/export supports
   them; record unavailable fields as unavailable.
4. Require a minimum comparable sample before making a recommendation.
5. Generate one-variable experiment briefs and a Git-safe weekly report.

Exit criteria: no fabricated metrics, stable joins by source plus variant,
recommendations cite sample sizes and measured deltas.

Rollback: retain new fields but disable recommendation generation.

## PR 8 — Bounded batch rollout

Model tier: strongest available for arbiter calibration; cheap model for orchestration.

Dependency: PR 6. PR 7 is preferred but not required for private drafts.

Context: rollout should test the system as a five-video package without running a
daemon or flooding the channel.

Primary files: weekly planner, CLI orchestration, operations docs, integration
tests.

Tasks:

1. Build one five-video batch matching the mix in creative spec section 13.
2. Run preflight and render sequentially at 720x1280 to N2ME.
3. Produce contact sheets, manifests, creative reports, and one batch index.
4. Require an autonomous release-arbiter pass before any platform request.
5. Upload private drafts first. Posting may be the sole optional operator action;
   automatic posting remains configurable.
6. Capture 24-hour and seven-day analytics after release and archive the batch
   decision.

Exit criteria: five admitted stories, five passing technical manifests, five
arbiter reports, no concurrent FFmpeg, no TikTok, no duplicate source, no public
upload from CI or implementation commands, and no required human editing.

Rollback: keep artifacts local/private and revert the batch planner feature flag.

## Adversarial review checklist

Before merging each PR, ask:

- Can a weak story game the score with keywords?
- Can narration omit the payoff while tests still pass?
- Can generic footage be labeled as proof?
- Can a render pass while holding one composition too long?
- Can an upload happen without an independent arbiter state?
- Can a missing metric be interpreted as zero?
- Can retries duplicate an upload?
- Can x264 ignore the intended resource cap?
- Can any path leak credentials or write large media to the internal drive?

Critical or high-risk findings block merge.

## Plan mutation protocol

Record mutations at the bottom of this file with date, affected PRs, reason,
new dependency edges, and rollback impact. Never silently expand a PR. Split it
when it changes more than two primary subsystems or cannot be reviewed in one
diff.

Mutation 2026-09-02: `docs/STUDIO_CRAFT_STANDARD_V3.md` raises the target craft
bar for talking points, footage, VFX, animation, voice, SFX, and final-cut review.
The existing PR 1–8 scopes and dependencies do not expand. The larger studio
capabilities are isolated in `plans/signal-forge-world-class-studio.md` PRs 9–22
after PR 8 proves the private five-video foundation. Rollback impact: none to the
v2 implementation sequence; the companion roadmap can be deferred independently.

## Definition of done

The program is complete only when one autonomous five-video batch passes the v2
creative and technical gates, stays under the host resource ceiling, reaches
private drafts without human editing, can be posted with one simple action or a
configured schedule, and produces joined 24-hour plus seven-day analytics. A
view target is an experiment objective, not evidence that implementation is
complete.
