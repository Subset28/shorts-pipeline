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
- `pytest -q`: 27 passed. `git diff --check`: passed.

## Remaining work

- Continue improving the creative quality from retention evidence rather than
  assuming any lane will go viral.
- Finish platform OAuth/configuration and perform a deliberate final-release
  review before deploying to the NAS.
