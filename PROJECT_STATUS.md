# Project status

## Shorts pipeline

2026-08-30: Added a deterministic weekly content planner that balances
categories, reserves a distinct long-form slot from approved Reddit sources,
writes private UTC publishing times, and separates planning from rendering and
uploading.
2026-08-30: Added bounded weekly production dispatch. Reviewed plans now have
a render-only execution path, optional private-Short upload mode, source
validation, an eight-entry cap, and an explicit TikTok-off boundary.

2026-08-30: Added channel-level YouTube packaging with bounded metadata,
category-aware tags, generated custom thumbnails, and idempotent thumbnail
retry state. Verified with 109 project tests, Ruff, compileall, and diff checks.
2026-08-30: Expanded analytics aggregation to preserve impressions, CTR,
average view duration, average percentage viewed, watch minutes, and
engagement. Reports now emit separate packaging and retention actions, with
low-CTR unit handling covered by tests.

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
