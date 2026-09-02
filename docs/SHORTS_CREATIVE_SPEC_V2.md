# Signal Forge Shorts Creative Specification v2

Status: governing creative contract for new Shorts work.

## 1. Product definition

Signal Forge is an entertainment-first technology channel about AI/ML, computer
science, cybersecurity, and the systems people depend on. A Short is not a
miniature lecture. It is a compressed story with a technical mechanism inside
it.

The viewer contract is:

> Show me something surprising, make the situation escalate, and pay off the
> question before I regret stopping.

Accuracy, permission, attribution, and upload safety remain hard gates. They do
not determine whether a video is entertaining enough to make.

## 1.1 Public-release quality floor

The existing utility voice, static Pillow cards, and generic
caption-over-footage treatment are development placeholders. Minecraft is a
valid public convention only for the permissioned Reddit-story lane; it is not
the universal Signal Forge visual system.

A public v2 Short requires:

- a 1080x1920 final master at 30 fps;
- a performed human or premium neural voice approved for that episode;
- source-specific footage, screenshots, artifacts, or recreations as the main
  visual layer;
- designed motion graphics rendered from the beat sheet;
- deliberate sound design and a normalized final mix;
- frame-by-frame typography with measured fit and no template overflow;
- an automated release-arbiter pass on the final encoded file.

720x1280, macOS TTS, and static cards may be used for low-cost development
previews only. They must be visibly labeled `PREVIEW` and are blocked from
public upload.

## 2. Creative order of operations

Every Short must satisfy these layers in order:

1. **Stop** — the first frame and first spoken line create immediate tension.
2. **Promise** — the viewer understands what answer, reveal, or outcome is coming.
3. **Escalate** — every beat changes the situation; no repeated explanation.
4. **Prove** — specific numbers, screenshots, diagrams, or source receipts make
   the story feel real.
5. **Pay off** — resolve the opening question with a concrete result or reversal.
6. **Echo** — end on a consequence that makes the opening worth replaying.

If a source is credible but cannot satisfy the first five layers, do not make it
a Short. It may be research material or a long-form source.

## 3. Audience and channel promise

Primary audience: curious 15–25-year-olds who recognize technology but do not
want a classroom introduction. They respond to stakes, status, danger, absurdity,
surprise, and impressive builds before terminology.

Channel promise: **the wildest true stories hiding inside modern technology**.

The channel should feel like a technically literate friend showing you the part
of the story everyone else skipped. It must not sound like a corporate explainer,
Reddit text-to-speech farm, or AI-generated book report.

## 4. Story admission score

Score each source from 0–100 before scripting. Record the evidence for every
non-zero score.

| Dimension | Points | Question |
| --- | ---: | --- |
| Immediate stakes | 0–20 | Can the consequence be understood in one sentence? |
| Curiosity gap | 0–15 | Does the source create a specific unanswered question? |
| Reversal or escalation | 0–15 | Does the situation materially change at least twice? |
| Visual proof | 0–15 | Are there usable receipts, diagrams, numbers, or cleared visuals? |
| Specificity | 0–10 | Are there concrete systems, amounts, errors, or constraints? |
| Human emotion | 0–10 | Is there panic, ambition, embarrassment, conflict, or awe? |
| Payoff strength | 0–10 | Is the ending more satisfying than the setup? |
| Channel fit | 0–5 | Is the mechanism genuinely AI/ML, CS, cyber, or engineering? |

Admission rules:

- **80–100:** priority production candidate.
- **70–79:** produce only if the visual plan is unusually strong.
- **Below 70:** reject for Shorts.
- Missing outcome, missing source permission, or unverifiable central claim is an
  automatic rejection regardless of score.
- Advice requests, open questions, generic career posts, product promotions,
  outrage without mechanism, and stories whose only hook is a large number are
  rejected.

Raw Reddit score is discovery evidence, not an admission dimension.

## 5. Repeatable story lanes

Use these lanes because each carries a built-in emotional engine:

1. **Technical catastrophe** — a normal action triggers a system-scale failure.
2. **Impossible build** — someone makes advanced technology run under absurd
   constraints.
3. **Hidden dependency** — one overlooked service, identity, cable, setting, or
   person controls the whole system.
4. **The obvious fix fails** — bigger models, more data, more money, or standard
   advice loses to an unexpected intervention.
5. **Cyber trap** — the dangerous step looks harmless until the attack chain is
   revealed. Defensive framing only.
6. **Human versus automation** — the machine fails because the missing
   information lives in a person's judgment or behavior.

Do not rotate lanes mechanically. Choose the lane already present in the source.

## 6. Short structure

Target 30–48 seconds and 75–110 spoken words. Longer is allowed only when every
five-second window introduces new information or a new visual state.

| Time | Beat | Requirement |
| --- | --- | --- |
| 0.00–0.70 | Cold open | Show the result, danger, impossible constraint, or strongest receipt. No logo. |
| 0.70–2.50 | Promise | State the contradiction and imply a specific answer. |
| 2.50–7.00 | Setup | Give only the context needed to understand the problem. |
| 7.00–16.00 | Escalation | Add the first failed attempt, dependency, or worsening consequence. |
| 16.00–28.00 | Mechanism | Reveal how the system actually behaves through action, not a definition. |
| 28.00–40.00 | Payoff | Deliver the outcome, number, fix, or reversal promised at the start. |
| Final 2–5 sec | Echo | Land the consequence or loop naturally into the opening image. |

The Reddit card is a receipt, not the video. It may appear for 0.8–2.0 seconds
after the cold open, then return briefly when a quote or outcome needs proof.

## 7. Script rules

Write for the ear and the cut:

- Start with conflict: “This chip generated a face with four million parameters.”
- Prefer active, present-tense sentences under 14 words.
- One sentence should usually correspond to one visual beat.
- Delay technical names until the viewer wants the explanation.
- Translate mechanism through consequence: “It streams the next layer from flash
  while the current one runs,” not “DMA improves memory efficiency.”
- Keep numbers only when they create scale, contrast, or proof.
- Attribute disputed or first-person claims without draining the hook.
- End on the source-backed result, not “follow for more,” “what do you think,” or
  a generic lesson.

Delete these on sight:

- “Here’s why this matters.”
- “In the world of technology.”
- “This Reddit user shared…”
- a full source headline read aloud before the story starts;
- definitions the viewer did not need;
- repeated summaries;
- unsupported superlatives;
- moral-of-the-story conclusions.

## 8. Visual grammar

Every Short needs a written visual beat sheet before rendering. Each beat must
name one dominant visual, its source/permission record, and the narration line
it proves.

Minimum visual rhythm:

- a first-frame artifact readable without audio;
- six distinct visual states in a 35–45 second Short;
- a meaningful pattern change every 1.5–3.0 seconds;
- no unchanged placeholder/background composition for more than three seconds;
- at least two source-specific proof visuals when the source supports them;
- one original mechanism visual: system map, counter, comparison, timeline, or
  animated callout;
- no decorative stock footage that implies an event it does not show.

Minecraft parkour is allowed in public `reddit_story` masters because viewers
recognize that loose, kinetic storytelling convention. It should make the story
feel casual and fast—not disguise a lecture. Use varied, clean footage; choose
cuts around story beats; keep captions and the Reddit receipt dominant; and
avoid inserting explanatory diagrams unless they make the conflict, joke, or
payoff more satisfying. Generic gameplay remains banned from non-Reddit lanes,
where source footage and designed visuals carry the story.

Shorts optimize entertainment, personality, tension, and replay. Long-form owns
the deep teaching, complete mechanism, evidence comparison, and portfolio-level
credibility. A Short may leave technical depth for its companion video as long
as its own promised story has a complete payoff.

Public masters use a Remotion composition driven by the structured beat sheet.
All animation is frame-driven; CSS and time-based browser animations are not
allowed. Sequences are premounted, duration is calculated from media and audio,
text is measured before render, and every asset is loaded through the managed
asset layer. FFmpeg remains the final encode, probe, and quality-verification
tool.

Per-episode minimum:

- 8–14 intentional shots for a 30–45 second Short;
- at least two source-specific proof assets;
- at least two original animated graphics or data/mechanism treatments;
- one brief source receipt;
- one visually dominant payoff shot that is not reused from the opening without
  meaningful transformation;
- no stock shot repeated inside the same Short;
- no unchanged full-screen template held longer than two seconds.

Frame hierarchy:

1. proof object or consequence;
2. one short caption phrase;
3. motion background;
4. source credit/receipt.

## 9. Captions and text

- Captions contain 2–5 words per burst and emphasize one word at a time.
- Use sentence case unless a specific alarm, error, amount, or reveal benefits
  from uppercase.
- Maximum two text regions on screen at once.
- The top headline disappears after the promise; it is not a permanent banner.
- Keep captions away from platform controls and do not cover the proof object.
- Animate emphasis with scale, color, or movement; do not animate every word in
  the same way.
- Captions must finish with the narration and remain readable at 720x1280.

## 10. Sound and narration

The audio should create momentum even with the screen hidden:

- begin with speech or a source-relevant sound in the first 100 ms;
- remove breaths, dead air, and pauses longer than 350 ms unless used for a reveal;
- vary pace: fast setup, brief hold before the reveal, clean final line;
- use cleared or original sound design only;
- use impacts, glitches, risers, or silence to mark real beat changes, not as a
  constant noise layer;
- do not publish robotic, mispronounced, or emotionally flat narration.

Public-release voice rules:

- macOS `say`, edge-TTS, and other utility voices are preview-only;
- the voice must perform changes in urgency, disbelief, restraint, and payoff;
- every technical name and proper noun is pronunciation-checked;
- narration is edited at phrase level, not accepted as one untouched TTS file;
- integrated loudness targets -14 to -16 LUFS with true peak at or below -1 dBTP;
- music and ambience duck 12–18 dB under narration;
- the mix contains a voice layer, a restrained bed, and beat-specific effects or
  purposeful silence.

If the available TTS cannot perform the script, rewrite for that voice or hold
the video. Do not hide weak narration under louder music.

## 11. Packaging

The title makes one accurate promise in 35–60 characters. It should expose the
contradiction without resolving it.

Good patterns:

- “The AI Model That Fits on a Microcontroller”
- “Ten Clicks Beat 575,000 ML Labels”
- “One Login Failure Took Down the Company”

Avoid source-title dumps, “you won’t believe,” keyword stacks, and hashtags in
the title. The description carries the source URL, author/subreddit attribution,
fact boundaries, and a concise channel-context sentence. Tags are spelling and
topic aids, not a growth strategy.

The first frame matters more than a separate Shorts thumbnail in the feed.
Design it as a poster: one object, one contradiction, readable in under half a
second.

## 12. Pre-publish creative gates

A video is blocked unless every answer is yes:

These gates are machine-enforced. The unattended worker does not wait for a
person to watch drafts.

### Attention gate

- Does frame one communicate tension without context?
- Is the first spoken line the strongest source-backed line?
- Is a clear promise established by 2.5 seconds?
- Does something materially change by 7 seconds?

### Story gate

- Does each beat add new information?
- Is there a real escalation and a real payoff?
- Can the ending be stated in one concrete sentence?
- Would the story still be interesting with the technical vocabulary removed?

### Visual gate

- Are there at least six distinct visual states?
- Does every visual either prove, clarify, or intensify the current line?
- Is no static composition held longer than three seconds?
- Is the source receipt visible but subordinate to the story?
- Is this a 1080x1920 final master rather than a labeled preview?
- If this is Reddit, is Minecraft functioning as polished kinetic support rather
  than a substitute for story progression? If it is not Reddit, is gameplay
  absent?
- Are at least two proof assets and two original motion treatments present?

### Polish gate

- Is the narration performed rather than merely synthesized?
- Are timing, transitions, type, color, and sound motivated by the current beat?
- Does any element look like a default template, debug card, or placeholder?
- Does frame one work as a silent poster and the payoff work as a standalone clip?
- Does the final encode look intentional when paused on any random frame?

### Trust gate

- Is the central claim supported by the recorded source?
- Are permission, author, subreddit, and URL present?
- Are inference and reported fact distinguishable?
- Does the video avoid pretending generic footage depicts the real event?

### Technical gate

- Do video and audio durations match within 100 ms?
- Do captions cover the complete narration?
- Does the render stay within the host resource profile?
- Is TikTok disabled unless explicitly authorized for that run?
- Was a low-resolution preview prevented from entering the public upload path?

### Autonomous release arbiter

The release arbiter runs after final encode and before any platform request:

1. Deterministic checks verify rights, source links, master resolution, duration,
   caption coverage, loudness, silence, visual-state count, receipt duration,
   text bounds, asset provenance, and forbidden placeholder fingerprints.
2. Whisper back-transcribes the final mix and compares it with the approved
   narration. Missing words, major substitutions, and pronunciation exceptions
   fail the candidate.
3. OCR and layout checks detect clipped text, unreadable captions, collisions,
   debug labels, and accidental credential-shaped strings.
4. A local multimodal critic receives the complete transcript, beat sheet,
   visual plan, contact sheet, opening clip, payoff clip, and low-resolution
   review encode. It scores the same attention, story, visual, trust, and polish
   rubric without access to the producer's self-score.
5. A second deterministic evaluator checks that the critic cited observable
   evidence for every pass. Unsupported ratings fail closed.
6. A failed candidate may trigger at most two targeted revisions. The failure
   report names the beat, asset, voice line, or mix problem to change. After two
   failures, the story is held and the worker moves to the next candidate.

The arbiter never weakens rights or factual gates, never fabricates a human
approval, and never publishes because a deadline or batch quota is approaching.
The only optional human action is the final posting command when automatic
posting is disabled.

## 13. Batch design and analytics

A production batch is five Shorts, not five random uploads:

- two technical catastrophes or hidden dependencies;
- one impossible build;
- one “obvious fix fails” or human-versus-automation story;
- one wildcard with the batch's strongest visual proof.

Only one variable changes inside a controlled comparison. Examples:

- result-first versus consequence-first opening;
- 32 seconds versus 44 seconds;
- source-receipt at 1 second versus 5 seconds;
- literal proof visuals versus original mechanism animation.

Capture at 24 hours and seven days:

- shown in feed / impressions where available;
- viewed versus swiped away;
- average view duration and average percentage viewed;
- retention at 1, 3, 5, 10, and 20 seconds;
- rewatches/loops where available;
- likes, comments, shares, subscribers, and watch time;
- story score, lane, duration, opening type, visual density, and voice.

Views are an outcome, not a controllable acceptance test. The production system
can guarantee source quality, creative discipline, packaging, safe rendering,
and measurement. It cannot guarantee distribution.

## 14. Current-batch editorial examples

### RP2350 image generator

- Lane: impossible build.
- Cold open: generated face beside the microcontroller and “4M PARAMETERS.”
- Promise: “This chip has less memory than one phone photo—so how is it making
  faces?”
- Escalation: weights do not fit conventionally; it streams them from flash.
- Mechanism: int8 model, DMA overlap, sparse activations.
- Payoff: a 128x128 image in roughly 20 seconds.
- Echo: return to the tiny board beside the generated face.

### 575,729 archival labels

- Lane: the obvious fix fails / human versus automation.
- Cold open: “575,729 labels lost to ten clicks.”
- Promise: “More data and a bigger model both failed.”
- Escalation: ResNet-50 and higher resolution fit training better but not unseen
  books.
- Mechanism: the missing variable was each operator's invisible crop preference.
- Payoff: ten corrections lifted held-out pass@80 from 0.71 to 0.83.
- Echo: “The pixels never contained the answer.”

These examples are beat directions, not final scripts. Final wording must be
checked against the complete source record.
