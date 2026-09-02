# Architecture

## Product contract and migration state

`SHORTS_CREATIVE_SPEC_V2.md` is the target product contract. The current
pipeline is source- and render-safe but does not yet implement the complete v2
story score, beat sheet, proof-asset plan, creative gate, or treatment-level
analytics. `plans/shorts-v2-retention-engine.md` is the authoritative migration
order. Code must not label a current artifact `v2_passed` until the structured
gate in PR 6 exists and all required evidence is present.

The target flow is:

```text
Reddit/API source
  -> permission and fact gate
  -> 100-point story admission score
  -> seven-beat story compiler
  -> proof-asset and visual-state plan
  -> sequential bounded renderer + rhythm-aware audio/captions
  -> technical quality gate + creative quality gate
  -> human review state
  -> private draft / explicit operator release
  -> 24-hour and seven-day treatment analytics
```

Each boundary emits inspectable JSON. No stage infers that the previous stage
passed from the existence of a file alone.

`sources.py` reads public feeds; `seo.py` creates a source-linked original
explanation; `tts.py` optionally calls the existing ElevenLabs rotating-key
helper; `render.py` produces a 9:16 MP4; and `publish.py` sends that asset to
YouTube and TikTok through their official APIs. The manifest makes retries and
future analytics joins deterministic.

`media.py` provides an explicit yt-dlp adapter for rights-cleared source media.
It is never part of topic discovery and never downloads playlists by default.

In v2, visual planning must distinguish source proof, original explanatory
graphics, and kinetic background. Background footage cannot satisfy a proof
requirement and cannot be labeled as depicting the source event.

`captions.py` uses local faster-whisper when installed and falls back to timing
the known narration text. The resulting SRT is burned into the final MP4 by
FFmpeg, so platform uploads do not depend on sidecar-caption support.

`content_calendar.py` turns the ranked source pool into a category-balanced
weekly slate with explicit private UTC publish times. Planning is separate from
rendering and publishing, so the operator can review the source and rights
fields before media work begins.

When an analytics report contains repeated evidence, the planner consumes its
experiment brief to prefer the measured reference category and annotate only
unambiguous baseline/reference targets. Format and variant remain explicit in
the plan; insufficient evidence leaves the normal rotation unchanged.

`editorial.py` turns each selected topic into a private research brief with a
source claim, creative treatment, visual and caption direction, metadata,
long-form bridge, and rights gate. `research-week` writes those briefs for
review; `plan-week --research` attaches them to the private production plan.
The research layer does not render or publish.
During short production, the validated brief is passed into package creation
so reviewed packaging choices survive into the generated hook and metadata;
the narration remains source-anchored.
During long-form production, the same validation applies the reviewed bridge,
question, and source-linked metadata to the narrated package.
Ready analytics experiments are also materialized in research briefs as
bounded hook or packaging treatments with their metric and control context.
Long-form composition adds a generated technical flow card after the opening
title card; this is the original-visual fallback when no Sora capability is
available.

The free path uses RSS, deterministic fallback copy, local Pillow rendering,
FFmpeg, and a required narration track. Optional LLM and TTS adapters improve quality without
changing the pipeline contract.

The v2 admission and creative gates remain deterministic. An LLM may propose
angles or wording, but it cannot grant permission, invent evidence, override a
rejection, claim human review, or mark unavailable analytics as zero.
