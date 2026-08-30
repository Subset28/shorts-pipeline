# Project status

## Shorts pipeline

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
- Finish platform OAuth/configuration and perform a deliberate final-release
  review before deploying to the NAS.
