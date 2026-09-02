# Low-cost agent handoff

Purpose: let a smaller coding model improve Signal Forge without rediscovering
the product, breaking publishing safety, or consuming the Mac's resources.

## Read this first

Read, in order:

1. `AGENTS.md`
2. `PROJECT_STATUS.md`
3. `docs/SHORTS_CREATIVE_SPEC_V2.md`
4. `docs/V2_DATA_CONTRACTS.md`
5. `docs/V2_EVAL_RUBRIC.md`
6. `plans/shorts-v2-retention-engine.md`
7. the files named in the assigned plan step

Do not read the whole repository unless the assigned step requires it.

## Product sentence

Build entertainment-first, source-backed Shorts about the wildest true stories
inside AI/ML, CS, cybersecurity, and engineering. The technical mechanism is
inside the story; it is not the opening lecture.

## Hard boundaries

- Never print or modify `.env`, `keys.json`, `client_secrets.json`, `token.json`,
  OAuth tokens, or API keys.
- Never infer reuse permission. Read the source record's permission field.
- Never download or publish uncataloged footage.
- Never invoke TikTok.
- Never upload publicly as part of implementation or testing.
- Never run an unattended daemon while developing.
- Never run more than one FFmpeg render at a time.
- Use `/Volumes/N2ME/Developer/shorts-pipeline` for source and ignored runtime
  media. Do not fill the internal drive.
- Use `RENDER_SIZE=720x1280`, `FFMPEG_THREADS=1`, and low priority for supervised
  test renders.
- Treat 720x1280, macOS `say`, edge-TTS, and static Pillow cards as preview-only.
  Minecraft is public-eligible only for `reddit_story` as polished kinetic
  support; it is forbidden in other lanes.
- Public v2 masters are 1080x1920 Remotion compositions with an approved
  performed voice, source-specific proof, original motion graphics, and a
  passing autonomous release-arbiter report.
- Stop a render if FFmpeg RSS approaches 750 MB. Preserve its log and diagnose
  before retrying.
- Work on a feature branch. Open a PR. Do not push directly to `main` or merge
  another agent's branch.

## One-task execution loop

1. Confirm branch and worktree:

   ```bash
   git status --short --branch
   git log -3 --oneline
   ```

2. Select exactly one incomplete blueprint step whose dependencies are merged.
3. Restate that step's acceptance criteria in a scratch note.
4. Write the smallest failing focused test.
5. Implement only the behavior needed for that test and the step's exit criteria.
6. Run the focused test, then the full suite:

   ```bash
   /Users/abba/shorts-pipeline/.venv/bin/python -m pytest -q path/to/focused_test.py
   /Users/abba/shorts-pipeline/.venv/bin/python -m pytest -q
   git diff --check
   ```

7. Review the diff for source truth, permissions, upload privacy, resource use,
   and accidental credential paths.
8. Update `PROJECT_STATUS.md` with what changed, evidence, and the next step.
9. Commit using `<type>: <description>`, push the branch, and open a PR containing:
   scope, creative impact, runtime impact, publishing/privacy impact, tests, and
   rollback.
10. Stop. Do not opportunistically begin the next PR.

## File map

| Concern | Primary files |
| --- | --- |
| Reddit discovery and source admission | `shorts_pipeline/reddit.py`, `tests/test_pipeline.py` |
| Editorial briefs and story scoring | `shorts_pipeline/editorial.py`, `tests/test_editorial.py` |
| Hooks, narration, titles, tags | `shorts_pipeline/seo.py`, `tests/test_pipeline.py` |
| Beat sheets and render manifests | `shorts_pipeline/models.py`, `shorts_pipeline/publish.py` |
| Cards, scenes, captions, final composition | `shorts_pipeline/render.py`, `shorts_pipeline/captions.py` |
| V2 motion composition | planned `video/` Remotion workspace and Python render adapter |
| Background and proof assets | `shorts_pipeline/media.py`, `shorts_pipeline/asset_library.py` |
| Scheduling and weekly production | `shorts_pipeline/content_calendar.py`, `shorts_pipeline/cli.py` |
| Analytics and experiment briefs | `shorts_pipeline/analytics.py`, `shorts_pipeline/youtube_reporting.py` |
| Host resource controls | `shorts_pipeline/resources.py`, `docs/OPERATIONS.md` |

## Decision tables

### Admit a story

- Permission missing: reject.
- Outcome missing: reject.
- Story score below 70: reject.
- Score 70–79: require a strong source-specific visual plan.
- Score 80+: eligible, subject to unseen-source and batch-balance checks.

### Choose an opening

- Impressive artifact exists: show it first.
- Catastrophic result exists: show the consequence first.
- Large contrast exists: show “before versus after” first.
- Only a headline exists: reject or hold for long-form research.

### Choose visuals

- Cleared source proof exists: use it.
- A mechanism can be diagrammed honestly: generate an original diagram.
- Only generic footage exists: use it as background, never as event evidence.
- Fewer than six visual states are possible: redesign or reject.

## Small-model failure traps

Do not:

- add more adjectives to make a hook “exciting”;
- read the Reddit headline verbatim as the opening;
- add “here's why this matters” or “follow for more”;
- treat Minecraft footage as sufficient story structure or use it outside the
  Reddit lane;
- summarize the same fact in setup, mechanism, and payoff;
- optimize tags while the opening is weak;
- accept a passing unit test as evidence that a rendered video is watchable;
- polish a Minecraft/TTS prototype instead of replacing the prototype stack;
- render repeatedly to debug code that can be tested by inspecting an FFmpeg
  command;
- change source-filter rules to force a weak batch through;
- claim views, privacy, or upload success without authoritative evidence.

## Required fixtures for creative work

Each new creative feature must include at least these source shapes:

- technical catastrophe with a closed outcome;
- impossible build with concrete constraints;
- open-ended advice post that must be rejected;
- promotional post that must be rejected;
- strong story with missing permission that must be rejected;
- first-person claim whose narration must preserve attribution.

## Render protocol

Code and command tests come first. Only after they pass may one supervised smoke
render run:

```bash
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"
export DOTENV_PATH=/Users/abba/shorts-pipeline/.env
export DATA_DIR=/Volumes/N2ME/Developer/shorts-pipeline/data
export OUTPUT_DIR=/Volumes/N2ME/Developer/shorts-pipeline/output/smoke
export RENDER_SIZE=720x1280
export FFMPEG_THREADS=1
export TTS_PROVIDER=macos
nice -n 10 /Users/abba/shorts-pipeline/.venv/bin/python -m shorts_pipeline run --dry-run --reddit-only --youtube-only
```

This command creates a preview, never a releasable master. Observe RSS from
another terminal. A completed preview must have a passing manifest, matching
audio/video duration, complete captions, and an automated report against every
gate in `SHORTS_CREATIVE_SPEC_V2.md`.

## Handoff report template

```markdown
Branch/PR:
Blueprint step:
Behavior changed:
Files changed:
Focused test:
Full suite:
Creative gate evidence:
Resource evidence:
Publishing/privacy impact:
Known limitations:
Next unblocked step:
```

If any field is unknown, say unknown. Do not fill it with assumptions.
