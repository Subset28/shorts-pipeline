# Project status

## Shorts pipeline

- The local pipeline is the working source of truth; NAS deployment is reserved
  for an explicitly approved finished release.
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
- Added the supplied Reddit avatar and verification graphics plus the public
  Reddit award collection. Reddit cards now choose eight deterministic award
  images per post and guarantee at least one animated award when available.
- Reddit story cards now preserve the complete post title independently from
  the shorter platform metadata title, so long hooks no longer end mid-sentence.
  The card itself is rendered as an 8-frame opening loop.
- Final Reddit-story demo passed with generated narration, captions, a 1080x1920
  H.264/AAC render, Minecraft motion footage, and the reference-style card.
  The implementation lane is complete; publishing remains permission-gated.
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
