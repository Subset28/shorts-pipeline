# Signal Forge world-class autonomous studio roadmap

Objective: evolve Signal Forge from an automated video pipeline into an
autonomous technology studio capable of finding important stories, developing
original editorial positions, producing premium visual and audio work, growing
an audience across Shorts and long-form, and building aligned revenue without
human editing.

Governing documents:

- `docs/CHANNEL_STRATEGY_V3.md`
- `docs/STUDIO_CRAFT_STANDARD_V3.md`
- `docs/SHORTS_CREATIVE_SPEC_V2.md`
- `docs/V2_DATA_CONTRACTS.md`
- `docs/V2_EVAL_RUBRIC.md`
- `docs/PRODUCTION_STACK_V2.md`

The current retention-engine PRs 1–8 remain the foundation. This roadmap begins
after PR 8 proves one five-video private batch. It may inform stricter acceptance
criteria in PRs 2–6, but must not silently expand those PRs.

## Non-negotiable invariants

- Original editorial work; no mass-produced recaps or copied expression.
- Every claim and asset has evidence, rights, provenance, and allowed-use data.
- Technology may be broad; the audience promise remains consistent.
- No human editing is required. Posting may remain the one optional operator act.
- Independent automated criticism is required before release.
- No public uploads from tests, CI, migrations, or implementation work.
- TikTok remains disabled unless a future operator decision creates a separate
  reviewed project.
- One heavy media job at a time on the Mac; N2ME holds active media; NAS holds
  durable approved artifacts; Windows rendering uses bounded SSH jobs.
- A missed slot is safer than a weak or unverified upload.
- Growth and revenue are measured outcomes, never guarantees.

## Dependency graph

```text
Retention engine PRs 1-8
        |
        +--> PR 9 Topic radar ---------> PR 11 Format portfolio
        |          |                              |
        |          +--> PR 10 Research dossier --+
        |                         |                |
        +--> PR 12 Media vault ---+--> PR 15 Autonomous short director
        |          |              |                |
        |          +--> PR 13 Motion/VFX system ---+
        |          +--> PR 14 Sound/voice system --+
        |                                           |
        +----------------------------------> PR 16 Long-form studio
                                                    |
PR 9 + PR 10 + PR 15 + PR 16 -------------> PR 17 Packaging lab
PR 15 + PR 16 + PR 17 --------------------> PR 18 Executive critic
PR 18 ------------------------------------> PR 19 Learning engine
PR 19 ------------------------------------> PR 20 Autonomous programming
PR 19 + PR 20 ----------------------------> PR 21 Revenue intelligence
PR 20 + PR 21 ----------------------------> PR 22 Scale qualification
```

PRs 12, 13, and 14 may be developed in parallel only when they do not touch the
same schema files. PR 15 integrates them. Every PR uses a feature branch, tests
first for code, full CI, an explicit resource/publishing impact statement, and a
reviewable rollback.

## PR 9 — Real-time technology topic radar

Model tier: default for collection/scoring; strongest available to calibrate
novelty and story-shape fixtures.

Context: “anything tech” needs broad discovery without becoming random. The
radar must detect timely opportunities and durable story leads while preserving
the single channel promise.

Build:

1. Define versioned `TopicSignal`, `TrendCluster`, and `RadarDecision` records.
2. Add adapters for authoritative RSS/APIs and approved communities across AI,
   cyber, software, hardware, robotics, internet platforms, gaming technology,
   aerospace, transport, energy, biotech, infrastructure, and tech policy.
3. Cluster duplicate coverage into one event and prefer primary evidence.
4. Score freshness, stakes, surprise, proof availability, story closure,
   authority, audience breadth, shelf life, and competitor demand separately.
5. Maintain fast-desk and premium-desk queues. Breaking candidates expire;
   evergreen candidates mature as evidence accumulates.
6. Add anomaly detection for sudden cross-source acceleration without treating
   raw popularity as admission.
7. Emit a Git-safe hourly digest and weekly opportunity map.

Tests: duplicate event fixtures, stale hype, embargo/speculation, one-source
rumor, closed incident, research paper with demo, category breadth, deterministic
ranking, API outage, and no-secret output.

Exit: the radar can discover across all tech, explain why each item matters now,
and safely return no candidate when evidence is weak.

Rollback: disable radar scheduling and retain existing source discovery.

## PR 10 — Research dossier and claim graph

Model tier: strongest available for dossier design; default for extraction and
verification passes.

Dependency: PR 9.

Context: proper talking points require more than summarization.

Build:

1. Add immutable dossier, claim, evidence, contradiction, uncertainty, talking
   point, and visual-proof schemas.
2. Require one thesis, three to five causal talking points for Shorts, source
   hierarchy, strongest limitation, closed result/current state, and prohibited
   exaggerations.
3. Resolve every factual sentence to claim IDs and every claim to one or more
   sources with source type and publication time.
4. Compare sources for disagreement and preserve uncertainty in narration.
5. Generate a claim-to-visual graph so scripting cannot outrun available proof.
6. Add freshness checks before render and again before scheduled publication.
7. Reject dossiers whose only value is importance, controversy, or a number.

Tests: conflicting reports, vendor benchmark, attributed first-person story,
updated outcome, retracted claim, open investigation, and fully closed case.

Exit: a fresh agent can understand what happened, why, what is unknown, what to
say, what to show, and what not to claim without reading raw browsing history.

Rollback: retain dossiers as private research artifacts.

## PR 11 — Show portfolio and format router

Model tier: strongest available.

Dependencies: PRs 9, 10, 15, and 16. Research can generate package concepts
earlier, but final thumbnail rendering and selection require real episode assets.

Context: topic breadth requires recognizable emotional formats.

Build:

1. Encode the ten lanes in `CHANNEL_STRATEGY_V3.md` as versioned format
   contracts, each with admission, proof, pacing, visual, sound, and payoff
   requirements.
2. Route by source story shape, not keyword or desired quota.
3. Choose Short, long-form, paired cluster, hold, or reject.
4. Add audience-breadth framing without deleting technical specificity.
5. Produce three distinct treatment concepts and select the strongest using
   source evidence and current format performance.
6. Enforce portfolio diversity only among independently eligible stories.

Tests: the same technical topic with catastrophe, build, policy, and advice
shapes; forced-format rejection; no-outcome hold; and treatment distinctness.

Exit: any admitted tech story receives a defensible format and treatment, while
weak stories remain rejected regardless of category demand.

Rollback: use the v2 lane selector.

## PR 12 — Rights-aware media vault and footage intelligence

Model tier: default.

Dependency: retention-engine PR 3.

Context: amazing footage comes from precise shot needs and a trustworthy vault,
not unrestricted downloading.

Build:

1. Implement the SQLite asset index and sidecar manifests defined in the
   production stack.
2. Add manifest-first ingest for permissioned video, images, documents, audio,
   fonts, models, and project files.
3. Generate low-resolution proxies, embeddings, technical metadata, scene cuts,
   OCR, dominant motion, and composition tags on N2ME.
4. Search by exact shot intent, claim ID, emotion, composition, movement,
   resolution, allowed use, and prior reuse count.
5. Add semantic deduplication and a visual-fatigue penalty.
6. Separate evidence, illustration, explanation, and atmosphere classes.
7. Sync immutable originals and manifests to the NAS; never sync credentials.
8. Reject uncataloged paths at planning and release.

Tests: permission mismatch, changed checksum, missing attribution, 9:16 crop
failure, duplicate clip, generic-footage demotion, NAS unavailable, and rebuild
from manifests.

Exit: every selected shot is relevant, technically usable, rights-cleared, and
traceable, and the system never searches the internal drive for media.

Rollback: run vault read-only while preserving current manifest selection.

## PR 13 — Motion design and VFX system

Model tier: strongest available for design system; default for component tests.

Dependencies: retention-engine PR 4 and PR 12 schemas.

Context: VFX must make invisible technology visible and give episodes authored
visual identities.

Build:

1. Create tested Remotion primitives for tracked callouts, device/screen
   composites, receipts, timelines, maps, counters, dependency graphs,
   before/after states, code/data transformations, depth/parallax, and guided
   focus.
2. Create parameterized Manim scenes for algorithms, network flows, model
   behavior, queues, attacks, measurements, and comparisons.
3. Create bounded scripted Blender hero scenes for devices, infrastructure,
   networks, machinery, particles, volumetrics, and impossible camera views.
4. Add effect-purpose metadata: prove, explain, intensify, transition, or payoff.
5. Generate episode palettes, materials, lighting, and motion motifs from the
   visual thesis while preserving core brand tokens.
6. Add golden frames, temporal-difference checks, OCR checks, and artifact
   detection for every primitive.
7. Enforce deterministic seeds, cached intermediates, one heavy job, and host
   resource budgets.

Tests: representative catastrophe, AI experiment, hidden dependency, cyber
chain, and impossible-build sequences; broken text; temporal artifact; default
preset overuse; and resource cancellation.

Exit: the system can build three clean, story-specific hero moments and multiple
supporting animations without manual keyframing or generic template output.

Rollback: feature flag individual VFX families; retain base Remotion renderer.

## PR 14 — Voice, sound effects, music, and sonic direction

Model tier: strongest available for voice/sonic benchmark; default for signal
processing and timing.

Dependency: retention-engine PR 5.

Build:

1. Define phrase-level performance direction: intention, pace, stress,
   pronunciation, emotional turn, breath, and silence.
2. Benchmark approved voices against real reference performances and reject
   utility cadence for public work.
3. Build a rights-cleared sonic library tagged by physical source, emotion,
   intensity, frequency profile, and allowed use.
4. Compile story beats into voice, bed, ambience, action, transition, reversal,
   payoff, and loop events.
5. Add deterministic ducking, loudness, peak, speech-intelligibility, silence,
   repetition, and phone-speaker checks.
6. Add sonic identity elements that remain subtle and never precede the hook.
7. Reject random whooshes, nonstop impacts, and the same music arc on every
   episode.

Tests: technical pronunciation, fast tension, quiet reveal, disbelief, long-form
fatigue, music masking, over-dense SFX, missing rights, and provider failure.

Exit: audio has a deliberate dramatic arc, the narration sounds performed, and
the public gate fails closed on quality or rights uncertainty.

Rollback: disable new sound compiler while retaining public voice blockers.

## PR 15 — Autonomous premium Short director

Model tier: strongest available.

Dependencies: PRs 10–14.

Build:

1. Convert the dossier and format into a visual thesis, 12–20-shot list,
   performance script, effect map, sound map, and packaging promise.
2. Require stop, promise, two turns, proof, mechanism, payoff, and echo without
   forcing identical timing.
3. Assign every shot a claim/talking-point ID and a primary visual job.
4. Build assets in dependency order, then assemble one canonical OTIO timeline.
5. Render preview, run deterministic checks, run independent picture/sound/story
   critics, and issue at most two targeted revisions.
6. Hold the story if a missing shot or weak payoff cannot be corrected honestly.
7. Produce a final-cut packet with contact sheet, opening/payoff clips, stems,
   claims, rights, treatment, package, critic evidence, and checksum.

Integration fixtures: all ten lanes, including polished Reddit/Minecraft support
and non-Reddit gameplay rejection.

Exit: three consecutive private Shorts pass the v3 craft standard without human
editing, placeholders, uncataloged media, or resource violations.

Rollback: retain v3 packets but use the v2 director.

## PR 16 — Autonomous long-form documentary studio

Model tier: strongest available.

Dependencies: PRs 10, 12, 13, and 14.

Build:

1. Add Case File, Build/Test, and System Story act schemas.
2. Compile 8–16 minute episodes with cold open, thesis, escalating acts,
   counterargument/limitation, visual proof, and resolved ending.
3. Create act-level visual motifs and shot economies; no single looping visual
   bed or endless captions.
4. Add original experiments/simulations where claims are reproducible and safe.
5. Generate chapters, citations, description, pinned-comment draft, and Short
   bridge assets from the same dossier.
6. Render in bounded act segments with resumable checkpoints and Windows SSH
   fallback.
7. Run independent story, factual, visual, audio, packaging, and endurance
   critics before private upload eligibility.

Tests: a failure reconstruction, original model test, historical systems story,
mid-render recovery, stale source, and an episode that must be cut rather than
padded.

Exit: one 8–16 minute private episode passes all gates, remains visually authored
throughout, and can be reconstructed exactly from its project bundle.

Rollback: preserve package and fall back to current private long-form path.

## PR 17 — Title, thumbnail, first-frame, and SEO laboratory

Model tier: strongest available for concept generation; default for validation.

Dependencies: PRs 9 and 10.

Build:

1. Generate concept families based on accurate consequence, contradiction,
   hidden cause, impossible constraint, or result.
2. Produce five long-form title and three thumbnail concepts; produce three
   Short first-frame/title pairs.
3. Render thumbnail candidates from episode assets, not unrelated generated
   faces or stock imagery.
4. Score mobile legibility, curiosity, specificity, emotional clarity, promise
   match, distinctness, and source support.
5. Add search-intent support for evergreen topics and browse packaging for
   stories, without keyword stuffing.
6. Store concept lineage and choose one controlled test variable.
7. Use YouTube-native testing interfaces when officially available; never swap
   packages in a way that destroys experiment attribution.

Exit: every episode has an accurate package that a new viewer can understand at
phone size, and the chosen package is not a paraphrase of a competitor.

Rollback: keep concepts as review artifacts and use current metadata.

## PR 18 — Executive producer and independent final-cut critic

Model tier: strongest available for calibration; cheaper independent models for
routine gates after benchmark.

Dependencies: PRs 15–17.

Build:

1. Add separate story, research, picture, VFX, sound, pacing, packaging, rights,
   and policy critic roles with immutable evidence schemas.
2. Require frame/timestamp/claim/asset citations; reject vibes-only praise.
3. Add disagreement handling and deterministic tie breakers.
4. Prioritize revisions by causal order: idea, thesis, script, assets, picture,
   sound, package.
5. Limit revisions to two and prohibit whole-episode regeneration when one
   component failed.
6. Build adversarial fixtures for polished-looking misinformation, technically
   perfect boredom, copied expression, fake evidence, excessive effects,
   robotic voice, and clickbait mismatch.

Exit: the critic reliably rejects every known slop mode and passes golden
episodes for observable reasons. Producer and critic identities remain separate.

Rollback: report-only mode; publication remains private/held.

## PR 19 — Audience learning and causal experiment engine

Model tier: strongest available for initial statistical contract; default for
weekly operation.

Dependency: PR 18.

Build:

1. Join appeal, engagement, satisfaction, return, subscriber, and revenue data
   to dossier, lane, thesis, hook, talking points, shot plan, voice, package,
   effects, sound, duration, and treatment lineage.
2. Store unavailable separately from zero and preserve metric definitions by
   API/version/date.
3. Compare matched cohorts and require minimum samples before recommendations.
4. Run one-variable experiments and estimate effect size plus uncertainty.
5. Detect retention cliffs at narrative/visual/audio events.
6. Generate keep/change/kill/replicate decisions with evidence and expiration.
7. Protect exploration so one early winner does not collapse the portfolio.

Exit: weekly decisions explain what changed, what happened, how certain the
result is, and which exact component should change next.

Rollback: archive metrics without automated decisions.

## PR 20 — Autonomous channel programming and release operations

Model tier: default; strongest available only for weekly slate arbitration.

Dependency: PR 19.

Build:

1. Maintain rolling fast-desk, premium-desk, Shorts, and long-form queues.
2. Schedule four to six passing Shorts weekly and one long-form every two weeks
   initially; failed gates create no upload.
3. Reserve resource windows and enforce one heavy job across Mac/Windows workers.
4. Recheck source freshness, rights, policy, and package immediately before
   release.
5. Keep uploads private until configured schedule/publication state; preserve
   idempotency and never invoke TikTok.
6. Collect 24-hour, 7-day, 28-day, and catalog-level outcomes.
7. Recover from network, API, host, and NAS failures without duplicate uploads.

Exit: four consecutive weeks run without human editing, duplicate uploads,
resource incidents, secret leakage, or quality-floor violations.

Rollback: pause scheduler and leave approved masters/private drafts intact.

## PR 21 — Revenue intelligence and commercial integrity

Model tier: strongest available for policy/offer design; default for monitoring.

Dependencies: PRs 19 and 20.

Build:

1. Add a versioned YouTube policy and eligibility monitor; never hard-code stale
   thresholds without effective dates and source URLs.
2. Track Shorts, watch-page, Premium, fan-funding, Shopping, affiliate, sponsor,
   and owned-product opportunities separately.
3. Add sponsor-fit scoring for audience relevance, claim verifiability,
   reputation, disclosure, creative fit, and conflict of interest.
4. Add affiliate/product gates requiring actual demonstration, honest negatives,
   and clear disclosure.
5. Build a sponsor media-kit dataset from verified public analytics, never
   estimates or competitor claims.
6. Optimize revenue per satisfied returning viewer and catalog value, not gross
   views alone.

Exit: the system can identify eligible revenue options and prepare truthful
commercial packets without altering an editorial conclusion or publishing a
deal automatically.

Rollback: disable commercial recommendations; keep audience analytics.

## PR 22 — Scale qualification, localization, and portfolio proof

Model tier: strongest available.

Dependencies: PRs 20 and 21.

Build only after four stable autonomous weeks and a real winning format:

1. Decide whether throughput, quality, or demand is the current bottleneck.
2. Scale only winning formats while keeping a measured exploration budget.
3. Evaluate dubbing/localization only with language-native quality and rights
   checks; never machine-translate jokes, claims, or technical terms blindly.
4. Generate public technical case studies showing the original systems,
   experiments, quality gates, and lessons without exposing credentials or
   private analytics.
5. Maintain a portfolio suitable for collaborators, sponsors, and college
   applications: architecture, research methods, responsible AI, media systems,
   measurable outcomes, and honest failures.

Exit: scaling increases output or reach without reducing median quality,
returning-viewer performance, trust, or host stability.

Rollback: return to the qualified single-language cadence.

## 90-day operating experiment after PR 18

### Weeks 1–2: private calibration

- Produce ten private Shorts across at least five lanes.
- Produce one private long-form pilot.
- Reject aggressively; tune critic thresholds against observable defects.
- No public cadence commitment.

### Weeks 3–6: controlled public launch

- Release up to four passing Shorts per week.
- Release one passing long-form episode every two weeks.
- Test opening, visual treatment, or package one variable at a time.
- Review 24-hour and 7-day metrics without overreacting to single uploads.

### Weeks 7–10: replicate real winners

- Give 60% of slots to formats with matched evidence of stronger appeal,
  retention, satisfaction, or return.
- Keep 30% for adjacent variations and 10% for genuinely new formats.
- Build one Short cluster into a stronger long-form episode.

### Weeks 11–13: catalog and business audit

- Audit channel promise, returning viewers, conversion to long-form, production
  cost, resource stability, and rights completeness.
- Keep, revise, or kill each lane with written evidence.
- Enable only revenue layers for which the channel is actually eligible and the
  audience relationship is ready.

## Adversarial plan review

Before each PR and monthly program change, ask:

- Are we mistaking expensive effects for a strong story?
- Can the talking points survive a skeptical technical reviewer?
- Does every hero shot prove, explain, or intensify this exact episode?
- Is “breaking news” merely unfinished news?
- Are broad tech categories attracting incompatible audiences, or does the
  emotional promise still unify them?
- Is a winner real after age, source, duration, and package differences?
- Can the autonomous critic detect polished misinformation and boring polish?
- Can any provider outage cause a low-quality fallback to publish?
- Can any retry duplicate, publicize, or mis-schedule an upload?
- Is revenue pressure changing conclusions, recommendations, or disclosures?
- Is the Mac or internal disk exposed to unbounded work?

Critical findings block the PR or slate.

## Definition of done

This roadmap is complete only when Signal Forge can autonomously discover,
research, write, direct, source, animate, composite, voice, sound-design,
package, privately stage, safely publish when configured, analyze, and improve
both Shorts and long-form technology videos for four consecutive weeks—with no
human editing, no rights ambiguity, no quality-floor exception, no duplicate
upload, and no host incident.

Views, subscribers, returning viewers, and revenue determine whether the studio
has found audience-product fit. They are not faked acceptance criteria and are
never guaranteed.
