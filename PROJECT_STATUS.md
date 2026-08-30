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
- Their creator names and pending-license status are recorded in
  `assets/user_backgrounds.json`; original channel URLs still need to be added
  before public publishing.
- `pytest -q`: 27 passed. `git diff --check`: passed.

## Remaining work

- Continue improving the creative quality from retention evidence rather than
  assuming any lane will go viral.
- Finish platform OAuth/configuration and perform a deliberate final-release
  review before deploying to the NAS.
