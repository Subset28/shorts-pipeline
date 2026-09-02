# Signal Forge v2 autonomous evaluation rubric

Status: normative pass/fail rubric for the independent release arbiter.

The producer cannot grade itself. The arbiter consumes the encoded candidate and
the immutable source/plan records. It does not see the producer's confidence,
deadline, queue size, or desired outcome.

## 1. Required evaluator inputs

- complete `SourceRecord` and claim matrix;
- `StoryAdmission`, demand evidence, beat sheet, visual plan, and audio plan;
- final render manifest and technical report;
- 1080x1920 encoded master;
- full transcript and word timings;
- frames at 0, 0.25, 0.5, 1, 2, 3, 5 seconds, every two seconds after that,
  every shot boundary, and the payoff midpoint;
- opening clip from 0–5 seconds;
- payoff clip plus final three seconds;
- OCR boxes, caption boxes, saliency regions, shot boundaries, perceptual hashes,
  loudness scan, silence scan, and back-transcription diff;
- asset provenance and generated-media declarations.

Missing input is a failure, not an invitation to estimate.

## 2. Deterministic blockers

Any blocker forces `hold` or `revise` regardless of critic score:

- missing/invalid permission, attribution, source URL, or claim evidence;
- preview, watermark, wrong dimensions, wrong frame rate, or corrupt output;
- audio/video delta over 100 ms;
- caption coverage below 100% of approved narration;
- text outside safe bounds or unresolved OCR collision;
- utility voice in a public candidate;
- gameplay outside the Reddit lane;
- Reddit gameplay labeled as evidence rather than kinetic support;
- uncataloged asset, changed checksum, or missing license record;
- generated illustration presented as real-event documentation;
- fewer than eight shots in a public master;
- static hold longer than two seconds without an explicit dramatic-hold marker;
- unmarked silence over 350 ms;
- loudness outside -16 to -14 LUFS or true peak above -1 dBTP;
- secret-shaped strings, debug labels, local absolute paths, or internal IDs on screen;
- revision count above two;
- producer and critic using the same model/prompt identity.

## 3. Attention score — minimum 85/100

| Criterion | Points | Full-credit evidence |
| --- | ---: | --- |
| First-frame stop | 20 | One dominant artifact/consequence and <=7 readable words; conflict is legible without audio |
| First spoken line | 20 | Strongest supported contradiction/result begins within 100 ms; no greeting/source preamble |
| Promise | 20 | Specific unresolved question or expected reveal is clear by 2.5 seconds |
| Early change | 15 | Material narrative and visual state change by 7 seconds |
| Forward pressure | 15 | No five-second window repeats the same claim or function |
| Replay echo | 10 | Ending reframes or visually returns to the opening without withholding the payoff |

Automatic attention caps:

- logo or branding before conflict: maximum 70;
- full Reddit headline read before promise: maximum 65;
- first sentence is context rather than tension: maximum 75;
- title-card-only first second: maximum 60.

## 4. Story score — minimum 85/100

| Criterion | Points | Full-credit evidence |
| --- | ---: | --- |
| Stakes | 15 | Viewer understands what can be lost, broken, won, or achieved |
| Causal progression | 20 | Each beat changes the state because of a source-backed action or constraint |
| Escalation/reversal | 20 | At least two meaningful turns; not a list of facts |
| Payoff | 25 | Opening promise resolves with the strongest concrete source-backed result |
| Compression | 10 | No removable definition, repeated summary, or generic conclusion |
| Tone/entertainment | 10 | Reddit is casual and fun; other Shorts remain vivid and conversational, never lecture-first |

Automatic story caps:

- missing source outcome: fail;
- generic “why it matters” ending: maximum 70;
- explanation occupies more time than action/escalation: maximum 79;
- premise works only for an already-expert viewer: maximum 75;
- payoff merely repeats the title: maximum 60.

## 5. Visual score — minimum 85/100

| Criterion | Points | Full-credit evidence |
| --- | ---: | --- |
| Story specificity | 20 | Main visuals correspond to this source, mechanism, artifact, or consequence |
| Shot rhythm | 20 | 8–14 intentional shots; pace changes with beats rather than a fixed timer |
| Hierarchy | 15 | One dominant object, one caption idea, clean safe zones, immediate scan path |
| Typography | 15 | Measured fit, consistent family/weights, purposeful emphasis, no template feel |
| Proof honesty | 15 | Proof, illustration, receipt, and kinetic support are visually distinct |
| Art direction | 15 | Color, motion, texture, and framing form an episode-specific but branded system |

Reddit-lane interpretation:

- polished Minecraft parkour may fill the kinetic layer;
- the post receipt, caption choreography, cuts, zooms, and story progression must
  still feel intentionally edited;
- educational diagrams are optional and should appear only when they increase
  tension, humor, or payoff;
- one continuous Minecraft clip with unchanged overlays is maximum 60.

Non-Reddit interpretation:

- gameplay is forbidden;
- source proof and designed motion carry the edit;
- at least two proof assets and two original motion treatments are required.

## 6. Polish score — minimum 85/100

| Criterion | Points | Full-credit evidence |
| --- | ---: | --- |
| Voice performance | 25 | Natural phrasing, emotional arc, correct pronunciations, no utility-TTS cadence |
| Mix | 20 | Clear voice, controlled bed, motivated effects/silence, target loudness and peak |
| Motion | 20 | Frame-accurate easing and emphasis; no default slideshow movement |
| Transitions | 10 | Motivated by beat/shape/action; no random preset rotation |
| Color and finish | 15 | Consistent contrast, grade, texture, sharpness, and readable mobile output |
| Artifact freedom | 10 | No clipping, malformed generated media, duplicate frames, jitter, or compression failure |

Automatic polish caps:

- untouched system/utility TTS: fail for public;
- static debug/Pillow card leads composition: maximum 50;
- generic yellow captions are the only design system: maximum 60;
- generated visual contains broken text/object continuity: maximum 70;
- music masks narration: fail deterministic mix gate.

## 7. Trust score — exactly 100/100

| Criterion | Points | Requirement |
| --- | ---: | --- |
| Claim coverage | 25 | Every factual narration line resolves to source claim IDs |
| Attribution | 20 | First-person/reporting status is preserved where required |
| Rights | 25 | Every production asset and source has allowed-use evidence |
| Visual honesty | 15 | Illustration and generic support never impersonate evidence |
| Metadata integrity | 15 | Title, description, source link, author/community, and disclosures agree with video |

Trust has no partial release. Any missing point blocks publication.

## 8. Evidence format

Every critic criterion returns:

```json
{
  "criterion_id": "attention.promise",
  "score": 18,
  "max": 20,
  "passed": true,
  "evidence": [
    {"kind": "frame", "id": "frame-60", "observation": "question text visible"},
    {"kind": "transcript", "start_ms": 1100, "end_ms": 2200, "text": "..."}
  ],
  "reason": "The exact promised reveal is clear by 2.2 seconds.",
  "revision": null
}
```

Evidence verifier rejects:

- vague terms such as “engaging,” “professional,” or “good” without observation;
- frame IDs outside the packet;
- transcript text not present at the cited timestamp;
- unsupported claims about viewer reaction;
- a score inconsistent with deterministic measurements;
- copied producer self-evaluation.

## 9. Critic prompt contract

System intent:

```text
You are an independent release critic for a premium technology Shorts channel.
Your job is to reject generic, educational-first, low-energy, visually empty,
robotic, misleading, or unfinished videos. You do not reward effort, deadlines,
technical correctness alone, or the producer's intentions. Grade only observable
evidence. Reddit stories may use polished Minecraft as kinetic convention and
should feel loose, fun, and fast. Non-Reddit videos may not use gameplay. The
payoff must be complete. Return only the declared JSON schema.
```

The user payload supplies immutable inputs and the rubric version. It never asks
“is this good enough?”; it asks for independent criterion evidence and a score.

The critic runs with temperature zero or the runtime's most deterministic mode.
Model, quantization, runtime, prompt, and rubric versions are recorded.

## 10. Decision algorithm

```text
if any trust or rights blocker: HOLD
else if any technical blocker is not correctable: HOLD
else if any technical blocker is correctable and revision < 2: REVISE
else if any dimension < 85 and revision < 2: REVISE weakest dimension
else if any dimension < 85: HOLD
else: PASS
```

When several dimensions fail, revise the earliest causal problem:

1. story/source admission;
2. opening/beat sheet;
3. visual plan/assets;
4. voice/performance;
5. render/mix/captions.

Do not polish a render whose story or opening failed.

## 11. Targeted revision mapping

| Failure | Allowed change | Must preserve |
| --- | --- | --- |
| Weak first frame | first shot/layout/text only | source claims, experiment variable, payoff |
| Promise late/unclear | cold-open and promise beats | claim meaning and total payoff |
| Lecture-first | remove definitions; move mechanism later | story causality and facts |
| Flat middle | shot plan and escalation compression | opening treatment and payoff |
| Weak payoff | select stronger source closure or hold | no invented outcome |
| Generic visuals | replace named shots/assets | narration claims and timing where possible |
| Flat voice | regenerate named phrases/provider | approved words and caption alignment regenerated |
| Caption collision | caption grouping/placement | narration and visual proof |
| Mix failure | gain, ducking, effects, silence | voice performance and edit timing |

## 12. Golden fixture suite

The implementation must ship synthetic/local fixtures with no publishing side
effects:

1. Strong Reddit catastrophe with polished Minecraft, casual voice, clear payoff:
   pass.
2. Same story with a static full-post card for eight seconds: visual fail.
3. Same story with utility TTS: polish blocker.
4. Strong non-Reddit AI build with gameplay: visual blocker.
5. Source-specific AI build with proof, motion, performed voice, and payoff: pass.
6. High-scoring open advice question with no outcome: admission reject.
7. Promotional tool launch with technical keywords: admission reject.
8. Strong story with permission missing: trust reject.
9. Generated reenactment labeled as actual incident footage: trust reject.
10. Perfect technical render with a context-first opening: attention fail.
11. Entertaining story whose captions omit the final sentence: technical fail.
12. Candidate scoring 84 in polish: revise once, not pass.
13. Candidate failing after revision two: hold.
14. Critic returning high scores without frame evidence: evidence-verifier fail.
15. Missing analytics represented as zero: analytics schema fail.
16. Repeated source with a new upload key but same treatment: idempotency fail.

Every fixture asserts failure code, state transition, and absence/presence of
platform calls.

## 13. Calibration set

Before the arbiter can release public masters:

- collect at least 20 internal candidates spanning known strong and weak states;
- label expected outcomes from the normative rubric during architecture setup;
- freeze source, frames, clips, transcripts, and expected deterministic results;
- require 100% agreement on blockers and >=90% agreement on pass/revise/hold;
- pin model/runtime/prompt after calibration;
- rerun calibration on every model, quantization, prompt, or rubric change;
- disable automatic public posting when calibration fails.

The initial architecture labels are a one-time system-design artifact, not an
ongoing video-editing intervention. Routine production remains unattended.

## 14. Anti-slop release assertion

The final release report must truthfully assert all of the following:

```text
The source earned production.
The opening earns the next second.
The story escalates instead of explaining in place.
The visuals are specific or intentionally conventional for the Reddit lane.
The voice performs the story.
The payoff resolves the promise.
Nothing on screen pretends to be evidence when it is not.
No placeholder crossed into the public master.
The producer did not approve itself.
The system can name exactly why this candidate passed.
```
