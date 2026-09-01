# Project status

2026-09-01: Tightened Reddit channel-fit selection after the live queue audit.
Personal advice, career, anxiety, recruiter, and other vague prompt titles are
now rejected at discovery and approved-queue load time; a concrete technical
incident must beat raw Reddit popularity. The weekly planner also prefers the
AI/ML, Cyber, CS, and engineering lanes whenever enough eligible topics exist.

2026-09-01: Aborted a supervised pilot after observing the final H.264
compositor reach roughly 887% CPU despite FFmpeg's global one-thread flags.
The final render now passes an explicit single-thread x264 profile and uses the
lower-cost `veryfast` preset; a command-level regression test covers it. No
upload occurred.

2026-09-01: Prevented silent TTS quality downgrades. If ElevenLabs is
configured but fails, production now stops instead of switching to edge-TTS;
the free fallback remains available only when ElevenLabs is not configured.
This prevents a failed premium voice from becoming an unreviewed upload.

2026-09-01: Added a bounded opening-and-pacing experiment for low-retention
lanes. Reviewed briefs marked `opening_and_pacing` now place the concrete hook
before the source headline while retaining the complete source-backed narration,
so the next batch can test the observed 6–9 second drop-off without changing
all packaging at once. Added a focused regression test and archived the
2026-09-01 dashboard snapshot in `docs/analytics/2026-09-01-dashboard.md`.

2026-08-31: Applied the one-thread FFmpeg profile to final short composition and preserved the last 1000 characters of FFmpeg diagnostics on render failure. A controlled static-background render failed with exit 234; its error is now actionable without exposing credentials.

2026-08-31: Made multi-segment background generation opt-in. Unattended runs now use one category/provenance-selected moving source by default, while `BACKGROUND_REEL_ENABLED=true` retains the richer reel for explicitly benchmarked hosts; this prevents the observed high-CPU reel path from running by default.

2026-08-31: Added a dedicated low-resource background encoding profile after a single-segment smoke render still reached roughly 568% CPU. Background segments now use one FFmpeg thread, bilinear scaling, and ultrafast encoding before stream-copy concatenation; final foreground/caption rendering settings remain unchanged.

2026-08-31: Replaced the multi-input background-reel graph with sequential per-segment renders plus stream-copy concatenation after an 8-input smoke render still reached roughly 430% CPU. The reel keeps source rotation, crop motion, and full duration while decoding one source at a time; focused tests pass.

2026-08-31: Bounded background-reel decoder fan-out after a render safety audit observed 22 simultaneous looping inputs and excessive CPU. Full-duration reels now use at most eight segments/inputs with adjusted pacing, preserving motion and coverage while reducing resource pressure; focused tests pass.

2026-08-31: Added an explicit `run --preflight` mode that validates Reddit queue, background, YouTube OAuth files, and TTS configuration without TTS, FFmpeg, or platform calls. Documented that `--dry-run` is render-only after a resource-safety audit observed high-CPU background generation.

2026-08-31: Strengthened source-backed YouTube packaging by adding up to four concrete terms from each source headline to the generated search tags, while retaining bounded metadata and existing source-link requirements. Focused metadata/editorial tests pass.

2026-08-31: Added `prepare-week --reddit-only` so reviewed weekly slates can be built deterministically from the approved Reddit queue without mixing in general RSS discovery. The mode remains planning-only and leaves permission records unchanged; targeted tests pass.

2026-08-31: Extended Reddit relevance tuning to aerospace and generic prompt threads after the second live audit. Aviation candidates now require a concrete mechanism plus an event arc, prompt-shaped titles need the same narrative evidence, and duplicate parent/comment stories are collapsed; technical flight incidents remain eligible.

2026-08-31: Tightened live Reddit selection after a 20-candidate discovery audit showed career and motivation prompts dominating the queue. Career-community and advice-shaped posts now require both a concrete technical mechanism and an event arc; the rule also applies to comment-derived stories.

2026-08-31: Verified the YouTube analytics launchd job was missing and loaded it successfully. Hardened the installer to verify every registered label with `launchctl print`; the analytics supervisor is now confirmed loaded without starting media production.

2026-08-31: Hardened the GitHub activity monitor for multi-agent work. It now watches PR/review/comment/push events, formats PR context in notifications, bounds `gh` and notification subprocesses, recovers from corrupt state, and writes state atomically.

2026-08-31: Made dotenv loading explicit for unattended jobs. `load_settings()` accepts `DOTENV_PATH`, and the YouTube analytics launchd script points to the verified runtime environment without printing or copying credentials.

2026-08-31: Added bounded FFmpeg resource controls for unattended renders. Video, background-reel, split, and long-form commands now default to two threads and single-threaded filter graphs; `FFMPEG_THREADS` is documented and clamped to 1-4 to reduce resource contention after the prior Mac crash report.

2026-08-31: Fixed the unattended analytics archive script to set the detached worktree on `PYTHONPATH` for both archive commands, so launchd can run from any working directory without import failures. Verified with shell syntax checks and the full test suite.

2026-08-31: Added a repository-safe weekly tuning log generator. The analytics archive workflow now records lane metrics, recommendations, and the structured experiment brief in readable Markdown alongside the aggregate JSON, making the next creative/SEO test explicit for review and Windows/NAS sync.

2026-08-31: Expanded the private research slate with a current AI-security candidate based on official OpenAI and UK AISI reporting. The brief labels vendor benchmark claims, separates incidents, and restricts visuals to defensive explanations; merged via PR #90.

2026-08-31: Weekly production preflight now requires every entry to carry a private, source-linked editorial brief with a hook, metadata, and tags; long-form entries also require a reviewed question and at least three chapters. This blocks unreviewed or weakly packaged weekly content before TTS, rendering, or upload.

2026-08-31: Tightened Reddit relevance filtering for the channel promise. Career/advice-shaped titles now require a concrete technical mechanism; generic career guidance is rejected while technical incidents remain eligible. The regenerated 2026-09-07 private plan contains 8 entries and no generic career-advice candidate.

2026-08-31: Added private editorial research slates. `research-week` now
turns source-backed topics into reviewable briefs containing evidence, hook,
format, visual direction, captions, metadata, long-form bridge, and rights
gates; `plan-week --research` attaches those briefs without rendering or
publishing.
The selector now prioritizes the channel's AI/ML, cyber, CS, and engineering
lanes before using score to fill the remaining slots, and chooses long-form by
channel relevance instead of raw source score. The 2026-09-07 slate was
generated and retained as a private review artifact.
Reviewed editorial briefs now flow into short-package generation and weekly
production, so approved hooks and metadata are applied only after source,
format, and private-status validation.
Long-form weekly entries now execute the reviewed question, chapter bridge,
source-linked metadata, and tags during narration/package creation.
Analytics experiment targets now flow into research briefs as explicit,
reviewable hook or packaging treatments with metric, role, and control context;
the next slate can test measured CTR and retention changes rather than merely
recording recommendations.
Weekly production now passes the scheduled publish time into long-form
execution and supports private YouTube upload plus thumbnail retry, matching
Shorts behavior without enabling TikTok or public publishing.
Weekly dispatch now also passes each plan entry's scheduled time into the
Short upload path, so the full private slate preserves its intended calendar.
Added `produce-week --preflight`, which validates a weekly plan and source
availability without invoking TTS, FFmpeg, or platform APIs. The real
2026-09-07 plan passed this preflight for all 8 entries.
Fresh source research on 2026-08-31 produced a private three-story AI,
cybersecurity, and networking slate with primary links, hooks, long-form
questions, visual treatments, and explicit fact boundaries in
`docs/research/2026-08-31-tech-story-slate.md`.
Upload paths now enforce a source-linked metadata gate: title, description,
tags, captions, category, and format are required, and Shorts must carry a
background visual before YouTube upload.
The enforcement path now raises on failed metadata evidence instead of merely
returning a failed report, so invalid packages cannot proceed to upload.
The unattended Reddit launchd job now runs as a background, low-priority,
throttled process to reduce resource contention during TTS and FFmpeg work.
Long-form renders now add an original technical flow visual after the opening
title card, giving the chapter-based explanation an intentional visual anchor
without requiring an unavailable Sora integration.
Added `prepare-week`, which discovers once and writes the private research
slate plus scheduled production plan with editorial briefs attached, reducing
duplicate discovery work before weekly production.
The preparation workflow now constrains the plan to the exact researched
source set, preventing an unresearched discovery candidate from replacing a
briefed weekly entry. The 2026-09-07 local artifacts were regenerated and
verified as private, scheduled, and fully briefed.
Weekly analytics now builds the planner-facing aggregate report automatically;
the YouTube Reporting API Reach Basic job supplies thumbnail impressions and
CTR while the existing activity query supplies retention and engagement.

## Shorts pipeline

2026-08-30: Added a deterministic weekly content planner that balances
categories, reserves a distinct long-form slot from source-backed topics,
writes private UTC publishing times, and separates planning from rendering and
uploading.
2026-08-30: Added bounded weekly production dispatch. Reviewed plans now have
a render-only execution path, optional private-Short upload mode, source
validation, an eight-entry cap, and an explicit TikTok-off boundary.
2026-08-30: Strengthened the long-form package with a six-chapter narrated
structure, source-versus-inference guardrails, chapter metadata, and a more
specific technical-analysis tag set.
Long-form renders now use the measured narration duration when available,
keeping the video timeline aligned with its audio instead of relying on a word
count estimate.

2026-08-30: Added channel-level YouTube packaging with bounded metadata,
category-aware tags, generated custom thumbnails, and idempotent thumbnail
retry state. Verified with 109 project tests, Ruff, compileall, and diff checks.
2026-08-30: Expanded analytics aggregation to preserve impressions, CTR,
average view duration, average percentage viewed, watch minutes, and
engagement. Reports now emit separate packaging and retention actions, with
low-CTR unit handling covered by tests.
2026-08-30: Added repository-safe analytics experiment briefs. Repeated lane
evidence now produces explicit packaging and opening/pacing tests with
baseline/reference metrics; thin samples produce no creative prescription.
2026-08-31: Connected experiment briefs to weekly planning. A ready brief now
prefers the measured reference category, preserves exact format/variant targets,
and records the strategy in the private review plan; incomplete evidence leaves
the normal rotation unchanged.

- The local pipeline is the working source of truth; NAS deployment is reserved
  for an explicitly approved finished release.
- The Synology NAS deployment was fully decommissioned on 2026-08-30. The
  Shorts Pipeline container, image, Compose network, and project directory were
  removed; the Mac mini is now the intended always-on runtime.
- The Mac mini is provisioned over direct SSH with the project,
  Python 3.13, FFmpeg-full, dependencies, Reddit assets, and Minecraft
  backgrounds. A dry-run render passed there; automatic publishing remains off
  until platform OAuth and permission-cleared Reddit records are configured.
- Mac YouTube OAuth was completed and a private AI News test upload succeeded;
  the returned YouTube ID is persisted on the Mac. TikTok remains disabled until
  its Direct Post access token is configured, and the persistent Mac `.env`
  remains `DRY_RUN=true`.
- Added channel-level YouTube packaging: titles are normalized to the platform
  limit, descriptions preserve readable paragraphs and topic context, tags are
  deduplicated and category-aware, and each short or long-form render gets a
  1280x720 custom thumbnail recorded in its manifest and sent to YouTube.
- Packaging follows current YouTube guidance: accurate titles/thumbnails,
  clear descriptions, and retention/CTR measurement over keyword stuffing.
- Current work adds source-gated content lanes: news breakdown, fact explainer,
  myth bust, technical joke/POV, question/answer, and conditional surprising
  fact, timeline, and prediction watch.
- Specialized lanes are enabled only when the title or source summary contains
  a matching signal. This prevents random format rotation from weakening the
  viewer promise.
- The latest four-variant dry-run completed with valid H.264/AAC MP4 outputs in
  `output/batch-13`.
- A render now requires a non-empty narration audio file; TTS failure stops the
  run instead of creating a silent short.
- Added two user-provided aerospace sources to the local library:
  `user_aerospire_cockpit.mp4` and `user_supkin_aerospace_edit.mp4`. A local
  aerospace render used both and produced a 1080x1920 H.264/AAC MP4.
- Verified the Minecraft parkour source as Creative Commons Attribution and
  recorded Orbital - No Copyright Gameplay's channel URL in the asset record.
  The local master is now downloaded at 1920x1080/60fps with the source audio
  retained for archival use.
- Generated 20 muted 45-second candidate clips in
  `data/backgrounds/minecraft_parkour_chunks`; Reddit-story renders prefer
  this library through `REDDIT_BACKGROUND_DIR`.
- Removed the obsolete Moon-to-Earth background from the local and Mac
  runtimes and disabled its automatic download fallback. Replacement footage
  will be added only after it is selected and its provenance is recorded.
- Added two user-selected YouTube background candidates at 1080p:
  `user_earth_zoom_space.mp4` and `user_rocket_launch_stock.mp4`. Their source
  URLs are recorded, but publication rights still need confirmation.
- Added category-aware background selection and per-render segment variation:
  sources are reordered, offset, subtly reframed, and concatenated so repeat
  renders do not reuse the same opening frames.
- Updated script-generation guidance to target format-specific duration bands:
  18-33 seconds for quick entertainment, 40-55 for explainers/news, and
  42-58 for complete Reddit stories when the source supports them.
- Reworked non-Reddit fallback hooks into short native Shorts headlines and
  tightened LLM guidance to reject generic topics without a concrete payoff.
- Strengthened the feed source gate so non-Reddit topics require a usable
  summary, preventing headline-only items from becoming shallow scripts.
- Added a completeness gate for RSS summaries, rejecting short or ellipsis-
  truncated feed text before it reaches narration or TTS.
- Preserved trailing punctuation during feed cleanup and changed long-source
  clipping to end at a complete sentence rather than speaking an ellipsis.
- Reject malformed replacement-character tails in RSS summaries so encoding
  corruption cannot become spoken narration.
- Expanded truncation detection to catch RSS markers wrapped as `[…]` or
  otherwise placed just before a closing bracket.
- Applied truncation detection after HTML cleanup as well as to raw feed text,
  covering ellipses followed by closing tags.
- Prefer fuller RSS `content` fields over truncated summaries when publishers
  provide them, preserving the source-quality gate without starving the queue.
- Hardened newsletter boilerplate removal for publisher HTML that inserts
  whitespace before punctuation.
- Fixed editorial-to-asset category aliases so AI News selects AI footage and
  Cyber selects cybersecurity footage instead of falling back to unrelated
  aerospace or general visuals.
- Mapped Finance explainers to neutral General motion footage when no
  finance-specific assets exist, preventing misleading cross-topic visuals.
- Tightened live source discovery with lane-specific minimum context and a
  low-signal ceremony filter, removing thin finance snippets and weak
  ribbon-cutting or honors entries before narration.
- Made the ceremony filter require concrete signal in the source summary,
  preventing generic title words such as “new” from bypassing it.
- Added content-level deduplication so newsletter and article mirrors of the
  same story do not consume separate non-Reddit queue slots.
- Extended deduplication to conservative near-mirror matching using shared
  title terms and high first-100-word similarity, covering lightly edited
  newsletter/article versions without broad topic matching.
- Calibrated the near-mirror threshold against the live Hugging Face
  newsletter/article pair so that confirmed duplicates collapse in practice.
- Made near-mirror comparison symmetric because lightly edited feed summaries
  can produce different sequence ratios depending on ingestion order.
- Narrowed multi-story “The Download” headlines to their lead story so the
  narrated subject, on-screen hook, and platform title remain aligned.
- Rebuilt background reels as 60-second sequences of varied, reframed shots,
  eliminating the former 8-second loop that repeated throughout longer shorts.
- Tightened the non-Reddit reel cadence to three-second shots, increasing the
  60-second assembly to 20 purposeful cuts for faster short-form pacing.
- Added a manifest quality report that records audio/video sync, background
  coverage, caption coverage, and explicit failure reasons for every render.
- Extended substantive non-Reddit news/explainer fallback context to support
  the intended longer runtime while retaining sentence-boundary clipping and
  refusing to pad thin sources.
- Applied the same sentence-boundary narration clipping to model-generated
  packages, preventing long non-Reddit scripts from ending mid-thought.
- Added an opt-in WhisperX diarization path (`WHISPERX_DIARIZATION=true` plus
  `HF_TOKEN`) that burns speaker-specific caption colors while preserving the
  existing aligned Whisper fallback when diarization is unavailable.
- Added `user_orbital_capsule_earth.mp4` (Aerospace) and
  `user_computer_typing.mp4` (CS) at 1080p; source URLs and rights notes are
  recorded in the asset manifest.
- Added the approximately one-minute `user_technology_loop.mp4` (CS) at
  1080p for varied long-form background sampling.
- Added `user_neon_city_drive.mp4` (CS) at 1080p; its source URL and rights
  note are recorded in the asset manifest.
- Added local 4K train-ride and city-pan footage as General motion assets;
  local placeholders are cataloged without attempting network downloads.
- Added local hacker-typing and malicious-hacker visuals as Cybersecurity
  assets; they are background-only footage and do not add operational content.
- Added two local code-typing clips to the CS category, including the
  MacBook typing clip just identified.
- Added the local high-end multi-monitor AI development setup clip to the AI
  category.
- Added the local robot clip to the AI category for robotics and future-tech
  stories.
- Added the supplied Reddit avatar and verification graphics plus the public
  Reddit award collection. Reddit cards now choose eight deterministic award
  images per post and guarantee at least one animated award when available.
- Reddit story cards now preserve the complete post title independently from
  the shorter platform metadata title, so long hooks no longer end mid-sentence.
  The card itself is rendered as an 8-frame opening loop.
- Final Reddit-story demo passed with generated narration, captions, a 1080x1920
  H.264/AAC render, Minecraft motion footage, and the reference-style card.
  The implementation lane is complete; the configured queue is operator-confirmed.
- The 20 configured Reddit candidates are operator-confirmed for reuse. Public
  YouTube-only mode is enabled; TikTok remains disabled.
- Reddit ranking now favors technical specificity, multi-step incidents, and
  explicit outcomes over raw score alone. A landscape long-form explainer path
  and `longform` CLI command are available for approved sources.
- Reddit narration now explicitly reads the post title first and the source body
  second. Caption sizing was increased for mobile readability. The final demo
  script uses a CS/TalesFromTechSupport-style production incident.
- Reddit discovery now rejects short bodies and off-topic generic AskReddit
  answers, maps dedicated communities into CS, AI/ML, Aerospace, or Cyber
  categories, and preserves source text through a complete-sentence boundary.
  A live API refresh produced niche candidates from sysadmin, programming,
  aerospace, aviation, and career communities; all remain uncleared until
  explicit reuse permission is documented.
- The review demo now uses a complete CS incident arc and renders at about
  45 seconds, establishing the first watch-time experiment band rather than
  treating a short 10–15 second sample as the finished story format.
- Reddit fallback treatments now add source-faithful narrative transitions,
  preserve the final source sentence as the outcome, and render a flowing
  title-plus-body card with no fixed dead-space minimum. The latest demo is
  about 46 seconds.
- Background rendering now uses Lanczos scaling, restrained post-scale
  sharpening, and CRF 18 encoding for cleaner portrait gameplay. The current
  Minecraft master is 1920x1080 landscape, so a native 4K or vertical source
  would be the next quality ceiling.
- Replaced the local Aerospire and Supkin background masters with fresh
  yt-dlp downloads: Aerospire is 1280x720/24fps (the source maximum), and
  Supkin is 1920x1080/60fps.
- Creator attribution and the source URL remain recorded in
  `assets/user_backgrounds.json`; verify the current upload license again
  before commercial publishing.
- Discovery now filters each feed by lane-specific relevance and rejects generic
  navigation titles or entries too thin to explain. Live discovery returned
  substantive AI, CS, aerospace, and finance topics after the filter.
- Added `docs/RESEARCH.md`, mapping hook, retention, format, and caption choices
  to current official YouTube guidance without claiming a guaranteed view count.
- Added a permission-gated `reddit_story` format. It supports real Reddit
  anecdotes only when author, subreddit, post URL, and explicit reuse permission
  are present; otherwise Reddit content cannot enter that lane.
- Added a ranked narrative-first subreddit configuration led by
  `TalesFromTechSupport`, `AskReddit`, aviation, sysadmin, and engineering
  communities rather than research-heavy technical feeds.
- `pytest -q`: 35 passed. `git diff --check`: passed.

## Remaining work

- Continue improving the creative quality from retention evidence rather than
  assuming any lane will go viral.
- Improved the no-Whisper caption fallback to break on natural punctuation and
  allocate timing by phrase length plus pause weight, while preserving the
  existing Whisper/WhisperX alignment paths.
- Restricted the technical-joke lane to sources with explicit humor or
  technical-culture signals, preventing serious AI and CS announcements from
  receiving mismatched generic POV scripts.
- Added a model source-fidelity gate that rejects generic non-Reddit drafts and
  anchors accepted narration to the exact source headline before TTS.
- Extended source anchoring to repair generic model hooks and platform titles
  from the source instead of allowing ungrounded metadata into publishing.
- Added a caption-density quality gate that rejects caption files which reach
  the end of the audio but contain too few words to represent the narration.
- Wired source and variant identity into background reel construction so
  repeated non-Reddit renders change their crop and pan sequence.
- Hardened background discovery to ignore zero-byte video placeholders before
  they can reach FFmpeg rendering.
- Finish platform OAuth/configuration and perform a deliberate final-release
  review before deploying to the NAS.
## 2026-08-31 — reduce final compositor CPU cost

- Changed the final gameplay compositor to crop to portrait before bicubic scaling, avoiding an expensive full-frame enlargement while preserving detail.
- This addresses the long-render FFmpeg failure path while preserving 1080x1920 output, captions, Reddit card animation, narration, and upload privacy behavior.
- Verification: bounded 0.1-second FFmpeg compositor diagnostic succeeded; `git diff --check` passed. Full pytest was unavailable because this checkout has no `.venv` and the shell has no `pytest`.
- Next: run a supervised full-duration smoke render only after the runtime checkout/dependencies are available; no upload was started.

## 2026-08-31 — improve technical-paper hooks

- Long research titles now produce a concise claim hook such as `WHY THIS ML METHOD REDUCES REDUNDANT EXPLORATION` instead of a truncated, generic `...MATTERS` hook.
- The exact source title and evidence remain in narration and metadata; this only improves the opening visual promise.
- Verification: direct fallback-package assertion, Python compilation, and `git diff --check` passed. Full pytest remains unavailable in this checkout.

## 2026-08-31 — fix launchd external-volume log failure

- Moved all launchd stdout/stderr targets from `/Volumes` to `/Users/abba/Library/Logs/shorts-pipeline`.
- The installer now creates the boot-volume log directory before registering jobs; this addresses silent `EX_CONFIG` 78 startup failures while keeping media and state on the external volume.
- Verification: all tracked plists lint, focused monitor test passes, and the launchd log-path assertions pass. No Reddit worker was reloaded.

## 2026-08-31 — bound GitHub monitor runtime

- Added a 45-second whole-process deadline to the GitHub activity monitor so a stuck API or notification path cannot remain resident under launchd.
- Deadline failures are reported to stderr and exit with a retryable temporary-failure status; no publishing code is involved.
- Verification: deadline-handler assertion, Python compilation, and `git diff --check` passed.

## 2026-08-31 — remove GitHub CLI dependency from monitor

- Replaced the launchd monitor's `gh` subprocess with a direct GitHub Events API request using the existing HTTP client and a 15-second request timeout.
- This avoids the launchd-only subprocess hang while preserving watched pull-request, review, comment, and push notifications without reading credentials.
- Verification: mocked HTTPS request contract passed with the runtime virtualenv; Python compilation and `git diff --check` passed.

## 2026-08-31 — make monitor startup dependency-light

- Replaced the monitor's third-party HTTP import with Python's standard-library URL client, retaining the 15-second network timeout and 45-second process deadline.
- This reduces launchd startup work and avoids import-time hangs on the external-volume source checkout.
- Verification: mocked URL request contract, Python compilation, plist lint, and `git diff --check` passed.

## 2026-08-31 — bound launchd notification delivery

- Notification delivery now has a three-second subprocess limit and reports failure without hanging the monitor.
- Event state advances only after all notifications succeed, so launchd retries missed alerts instead of silently dropping them.
- Verification: direct notification-failure/state-preservation assertion and `git diff --check` passed.

## 2026-08-31 — supervised full-duration render evidence

- Completed a single-thread, low-priority 51.936-second Reddit-style smoke render using existing narration, Minecraft footage, animated Reddit card, and captions.
- Artifact verified as 1080x1920 H.264/AAC at 30 fps; video/audio duration delta was 0.000 seconds, with 44 caption dialogues reaching the final timestamp.
- No upload occurred. Weekly production remains gated on reviewing the artifact and keeping the host resource-safe.
