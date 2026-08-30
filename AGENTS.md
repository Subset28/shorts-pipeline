# Mac mini Codex handoff

This repository is the source of truth for the unattended Shorts pipeline.
The Mac mini is the primary always-on compute host. The Synology DS1019+ is
best used for storage, backups, and optional artifact sync; do not make it the
main FFmpeg or Whisper worker.

## First actions on the Mac mini

1. Read `PROJECT_STATUS.md`, `README.md`, `docs/OPERATIONS.md`,
   `docs/ARCHITECTURE.md`, and `docs/STYLE_GUIDE.md`.
2. Check `git status`, pull the latest `main`, and never overwrite local user
   changes without inspecting them first.
3. Confirm Python 3.10+ is active before creating the virtual environment;
   macOS system Python 3.9 is not supported. Install `requirements.txt` and
   the optional captions extra when local `faster-whisper` is desired.
4. On Apple Silicon, put `/opt/homebrew/opt/ffmpeg-full/bin` before
   `/opt/homebrew/bin` in the worker's PATH; the regular Homebrew FFmpeg build
   may not include the libass `subtitles` filter.
5. Copy `.env.example` to `.env`, then configure secrets locally. Never commit
   `.env`, `keys.json`, OAuth tokens, client secrets, or API keys.
6. Begin with `python -m shorts_pipeline run --dry-run` and inspect the MP4
   before enabling any publishing.

## Runtime model

Run the Mac worker as a restartable `launchd` service. It should execute the
project daemon or an equivalent supervisor, preserve `data/` and `output/`,
write useful logs, and stop safely on missing credentials or failed TTS.
The pipeline must remain useful without an interactive Codex session. Codex
is the engineering/orchestration assistant for improving, diagnosing, and
reviewing the worker; it is not a required open chat connection.

The NAS may receive completed media and backups over the private home LAN.
Do not expose an upload/control endpoint to the internet, add router port
forwards, or copy credentials to the NAS unless a specific deployment review
approves it.

## Product priorities

- Produce watchable, original, source-backed vertical videos.
- Reddit records in the configured publishing queue are operator-confirmed for
  reuse; preserve author, subreddit, URL, and permission fields in manifests.
- Preserve the Reddit reference treatment: real-looking compact white post card,
  avatar, verification badge, award row with motion, complete title text,
  footer metrics, high-quality motion background, and accurately timed captions.
- Treat YouTube and TikTok publishing as separate idempotent state machines.
- Use analytics and retention evidence to choose formats; never promise viral
  performance or publish unverified/copyright-uncleared material.

## Change discipline

Use the smallest safe change, add or update focused tests, run `pytest -q` and
`git diff --check`, update `PROJECT_STATUS.md`, and commit working milestones.
Do not deploy to the NAS without an explicit final-release approval. Public
YouTube publishing is configured locally for the confirmed queue; TikTok stays
disabled. Keep all durable progress in
`PROJECT_STATUS.md`, not in private transcripts.

## Multi-agent coordination

All Codex/Claude agents must work on feature branches and communicate changes
through pull requests. Do not push directly to `main`, force-push, or merge
another agent's branch automatically. Before opening a PR, include tests,
runtime impact, publishing/privacy impact, and any required manual review.

## Useful commands

```bash
python -m shorts_pipeline run --dry-run
python -m shorts_pipeline batch --count 3 --dry-run
python -m shorts_pipeline reddit --count 10
python -m shorts_pipeline report --metrics metrics.csv
pytest -q
```
