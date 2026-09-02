# Competitor and format intelligence specification

Purpose: continuously learn what earns attention in technology/science Shorts
without copying another channel's script, edit, branding, or footage.

The supplied faceless-channel transcript contributes workflow hypotheses, not
verified revenue or algorithm facts. Adopt the research loop; reject the hype.

## 1. What the system adopts

- Analyze a cohort of successful channels before choosing a batch.
- Identify age-normalized outlier videos, not merely all-time view leaders.
- Extract topic shape, opening type, duration, shot cadence, proof density,
  caption behavior, voice energy, payoff timing, and loop structure.
- Turn every script into a timestamped scene plan before generating media.
- Prefer real permissioned/source visuals; generate only shots that cannot be
  sourced honestly.
- Publish controlled variations, collect results, and repeat measured winners.

## 2. What the system rejects

- Revenue estimates presented as audited fact.
- “Aged channel” or fake engagement warm-up tactics.
- Automated likes, comments, subscriptions, or feed manipulation.
- Copying a competitor's wording, shot order, distinctive concept treatment, or
  branding.
- Downloading competitor footage for reuse without a permission record.
- Account farms, free-tier rotation, identity spoofing, quota evasion, or any
  attempt to obtain “unlimited” access by bypassing a provider's controls.

## 3. Research cohort

Maintain 10–20 channels across:

- AI/ML builds and failures;
- cybersecurity incidents and defensive stories;
- computer-science curiosities;
- engineering and science mini-documentaries;
- adjacent high-retention fact/story channels used only for format analysis.

The cohort is reviewed automatically each week. A channel enters only when it
has at least ten relevant Shorts and enough public metadata to establish a
baseline. Store channel ID, niche, language, upload cadence, median recent views,
and last refresh time.

## 4. Outlier calculation

For each Short, record public metadata available through the official YouTube
API or authorized export:

- publication time;
- views, likes, comments, and duration;
- views per elapsed hour/day;
- ratio to the channel's rolling median for similar-age Shorts;
- title and available caption/transcript text;
- whether the video is still accelerating.

Define:

```text
velocity = views / max(hours_since_publish, 6)
channel_outlier = views / median_views_of_10_nearest_age_comparables
engagement_rate = (likes + comments) / max(views, 1)
```

These are research features, not guarantees. Flag a candidate pattern only when
at least three independent channels show comparable outliers.

## 5. Automated creative extraction

For research use, create a low-resolution analysis proxy and sample frames at
0.0, 0.5, 1, 2, 3, 5 seconds, then every two seconds. Do not place competitor
media in the production asset library.

Extract:

- exact first spoken proposition;
- first-frame object and text count;
- hook archetype: consequence, impossible constraint, question, reversal,
  before/after, confession, or visual spectacle;
- timestamp of context, first escalation, mechanism, and payoff;
- shot count and median shot length;
- proportion of source proof, generated visual, motion graphic, face, and filler;
- caption words per burst and emphasis behavior;
- music/sound-event density;
- ending type and whether it loops.

The report stores abstract patterns and metrics. It must not store a “rewrite
this script” prompt.

## 6. Topic demand score

Story admission remains source-first. Competitor evidence adds a separate
0–20 demand score after the source passes the 70-point creative admission gate:

- 0–5: topic appears in recent outliers across independent channels;
- 0–5: opening archetype has repeated evidence in the target niche;
- 0–5: the source offers stronger proof or a fresher reversal than references;
- 0–5: Signal Forge can create a clearly distinct visual treatment.

Demand score orders eligible stories. It cannot rescue a weak, unpermissioned,
open-ended, or visually unsupported source.

## 7. Generator adapter policy

AI video tools, including Higgsfield or future alternatives, sit behind one
optional adapter. The adapter:

- uses one authorized account and official access only;
- respects free-plan quotas, rate limits, output terms, and attribution rules;
- caches by prompt, model, settings, seed, and input hashes;
- stores provider, model, generation time, prompt, seed, source inputs, and
  rights terms in the asset manifest;
- never retries through another identity to evade a limit;
- fails over to a local Blender, Manim, or Remotion treatment when quota ends;
- never represents generated footage as documentation of a real event;
- rejects unreadable text, malformed interfaces, broken physics, inconsistent
  objects, or temporal artifacts.

Generated media is a designed illustration. Source receipts and real evidence
remain visually distinct.

## 8. Weekly output

Write a Git-safe research packet containing:

- cohort and refresh timestamp;
- top age-normalized outliers;
- repeated topic and hook patterns with sample sizes;
- pattern confidence and contradictory evidence;
- five admitted Signal Forge stories ranked by admission plus demand score;
- one treatment hypothesis per story;
- prohibited similarities to avoid;
- no credentials, cookies, downloaded competitor media, or private analytics.

The batch planner consumes the packet only when it is current and complete.
Missing research falls back to source scoring, not made-up “viral” advice.
