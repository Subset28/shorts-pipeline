# Signal Forge v2 data contracts

Status: normative interface contract for the v2 implementation.

All production records are immutable, versioned, JSON-serializable values.
Stages return new records and append events; they do not mutate an earlier stage
in place. Unknown fields are rejected at system boundaries until a schema
migration explicitly allows them.

## 1. Common conventions

- Timestamps: RFC 3339 UTC with `Z`.
- Durations: integer milliseconds.
- Frame positions: integer frames plus declared fps.
- Paths: project-relative or configured storage-root-relative; never secret/home
  expansion.
- URLs: canonical HTTPS source URLs.
- Scores: integers in their declared closed range.
- Hashes: lowercase SHA-256 hex.
- IDs: deterministic where specified; random IDs are forbidden for idempotent
  production entities.
- Optional means explicitly nullable. Missing required fields are invalid.

Deterministic IDs:

```text
source_id    = sha256(canonical_source_url)
story_id     = sha256(source_id + source_content_sha256 + creative_spec_version)
treatment_id = sha256(story_id + treatment_name + treatment_version)
asset_id     = sha256(asset_bytes)
render_id    = sha256(treatment_id + beat_sheet_sha256 + visual_plan_sha256
                      + audio_plan_sha256 + renderer_version)
upload_key   = sha256(render_id + platform + channel_id + privacy + publish_at)
```

## 2. Source record

```json
{
  "schema_version": "source.v2",
  "source_id": "sha256",
  "platform": "reddit",
  "canonical_url": "https://www.reddit.com/...",
  "title": "original title",
  "body": "complete approved source body",
  "author": "username",
  "community": "MachineLearning",
  "published_at": "2026-09-01T00:00:00Z",
  "captured_at": "2026-09-02T00:00:00Z",
  "content_sha256": "sha256",
  "permission": {
    "status": "verified",
    "basis": "written_permission",
    "allowed_uses": ["youtube_short", "youtube_longform", "derivative"],
    "commercial_allowed": true,
    "attribution_required": true,
    "evidence_ref": "private-local-reference",
    "verified_at": "2026-09-02T00:00:00Z"
  },
  "central_claims": [
    {
      "claim_id": "claim-01",
      "text": "source-grounded claim",
      "evidence_quote_hash": "sha256",
      "status": "reported_first_person"
    }
  ]
}
```

Rules:

- Production receives complete source text, not only a truncated discovery
  snippet.
- `permission.status` must be `verified`; global assumptions do not replace the
  per-source record.
- `evidence_ref` identifies private evidence without embedding credentials or
  private correspondence in Git.
- Central claim status is one of `verified_primary`, `reported_first_person`,
  `reported_secondary`, or `inference`.
- A content-hash change creates a new `story_id` and invalidates downstream
  approval.

## 3. Story admission

```json
{
  "schema_version": "story-admission.v2",
  "creative_spec_version": "2.0",
  "story_id": "sha256",
  "source_id": "sha256",
  "lane": "impossible_build",
  "hard_gates": {
    "permission": {"passed": true, "evidence": ["permission.evidence_ref"]},
    "closed_outcome": {"passed": true, "evidence": ["claim-04"]},
    "central_claim_support": {"passed": true, "evidence": ["claim-01"]},
    "non_promotional": {"passed": true, "evidence": ["rule-id"]},
    "channel_fit": {"passed": true, "evidence": ["rp2350", "quantization"]}
  },
  "dimensions": {
    "immediate_stakes": {"score": 18, "max": 20, "evidence": ["claim-01"]},
    "curiosity_gap": {"score": 14, "max": 15, "evidence": ["claim-02"]},
    "reversal_escalation": {"score": 12, "max": 15, "evidence": ["claim-03"]},
    "visual_proof": {"score": 13, "max": 15, "evidence": ["asset-candidate"]},
    "specificity": {"score": 10, "max": 10, "evidence": ["4M", "128x128"]},
    "human_emotion": {"score": 7, "max": 10, "evidence": ["astonishment"]},
    "payoff_strength": {"score": 9, "max": 10, "evidence": ["claim-04"]},
    "channel_fit": {"score": 5, "max": 5, "evidence": ["edge ML"]}
  },
  "total": 88,
  "decision": "admit",
  "rejection_codes": [],
  "scorer_version": "story-scorer@1"
}
```

Allowed lanes:

- `technical_catastrophe`
- `impossible_build`
- `hidden_dependency`
- `obvious_fix_fails`
- `cyber_trap`
- `human_vs_automation`

Decision rules:

- Any failed hard gate forces `reject`.
- Total below 70 forces `reject`.
- Total 70–79 sets `conditional_visual`, requiring visual-proof score >=13.
- Total >=80 sets `admit`.
- Total must equal the exact dimension sum.
- Evidence entries must resolve to source claims or asset-candidate records.

## 4. Demand evidence

```json
{
  "schema_version": "demand-evidence.v2",
  "story_id": "sha256",
  "cohort_version": "2026-W36",
  "independent_channel_count": 3,
  "topic_pattern": {"score": 4, "max": 5, "examples": ["reference-id"]},
  "opening_pattern": {"score": 4, "max": 5, "examples": ["reference-id"]},
  "proof_advantage": {"score": 5, "max": 5, "evidence": ["claim-02"]},
  "distinct_treatment": {"score": 5, "max": 5, "evidence": ["treatment-note"]},
  "total": 18,
  "expires_at": "2026-09-09T00:00:00Z"
}
```

Demand evidence orders admitted stories only. It cannot alter a hard gate or
admission score.

## 5. Beat sheet

```json
{
  "schema_version": "beat-sheet.v2",
  "story_id": "sha256",
  "treatment_id": "sha256",
  "format": "reddit_story",
  "target_duration_ms": 38000,
  "word_count": 96,
  "opening_type": "impossible_constraint",
  "beats": [
    {
      "beat_id": "cold-open",
      "role": "cold_open",
      "target_start_ms": 0,
      "target_end_ms": 700,
      "narration": "Four million parameters. On this.",
      "claim_ids": ["claim-01"],
      "promise_ids": ["promise-01"],
      "visual_intent": "generated result beside physical chip",
      "emphasis_words": ["four million", "this"],
      "energy": "impact",
      "transition": "hard_cut"
    }
  ],
  "promises": [
    {
      "promise_id": "promise-01",
      "question": "How can the model run under the chip's memory constraint?",
      "resolved_by_beat": "payoff"
    }
  ],
  "compiler_version": "beat-compiler@1"
}
```

Required roles in order:

```text
cold_open, promise, setup, escalation, mechanism, payoff, echo
```

Rules:

- Every spoken sentence belongs to exactly one beat.
- Every beat except `echo` introduces a new claim, state, or consequence.
- All promises resolve by `payoff`.
- Payoff retains source closure and cannot be removed to satisfy word count.
- Shorts target 75–110 words. Reddit may use a casual register; long-form owns
  exhaustive explanation.
- `transition` is one of `hard_cut`, `match_cut`, `whip`, `push`, `wipe`,
  `focus_pull`, `receipt_flash`, or `none`.

## 6. Visual plan

```json
{
  "schema_version": "visual-plan.v2",
  "treatment_id": "sha256",
  "format": "reddit_story",
  "shot_count": 11,
  "shots": [
    {
      "shot_id": "shot-01",
      "beat_id": "cold-open",
      "start_ms": 0,
      "end_ms": 700,
      "kind": "source_proof",
      "asset_ids": ["sha256"],
      "layout": "hero_split",
      "motion": "snap_scale",
      "caption_zone": "lower_safe",
      "claim_ids": ["claim-01"],
      "evidence_role": "proves",
      "generated_media_disclosure": null
    }
  ],
  "receipt": {
    "start_ms": 900,
    "end_ms": 2200,
    "source_id": "sha256"
  },
  "background_policy": {
    "kind": "minecraft_parkour",
    "allowed": true,
    "reason": "reddit_story kinetic convention",
    "evidence_role": "kinetic_only"
  },
  "planner_version": "visual-planner@1"
}
```

Shot kinds:

- `source_proof`
- `permissioned_source_clip`
- `original_motion_graphic`
- `original_3d`
- `generated_illustration`
- `reddit_receipt`
- `kinetic_background`

Rules:

- Shots cover the complete target duration with no gap or overlap unless the
  overlap is an explicit transition.
- Non-Reddit formats reject gameplay backgrounds.
- Reddit may use Minecraft only with `evidence_role=kinetic_only`.
- Generated illustrations are labeled internally and cannot claim to depict the
  real event.
- Public master requires at least eight shots. Non-Reddit requires at least two
  proof assets and two original motion treatments. Reddit requires a complete
  receipt, polished kinetic progression, and at least two source-specific visual
  moments where the source supplies them.
- Any asset permission or checksum change invalidates the plan.

## 7. Asset record

The normative asset schema is in `PRODUCTION_STACK_V2.md`. Add these machine
fields:

```json
{
  "validation": {
    "decode_passed": true,
    "width": 1920,
    "height": 1080,
    "duration_ms": 4800,
    "has_audio": false,
    "ocr_text": [],
    "placeholder_fingerprint": false
  },
  "generation": {
    "provider": null,
    "model": null,
    "prompt_sha256": null,
    "seed": null,
    "terms_snapshot_ref": null
  }
}
```

## 8. Audio plan

```json
{
  "schema_version": "audio-plan.v2",
  "treatment_id": "sha256",
  "voice": {
    "provider": "elevenlabs",
    "voice_id_ref": "non-secret-alias",
    "public_eligible": true,
    "performance_direction_version": "voice-direction@1",
    "pronunciations": {"RP2350": "R P twenty-three fifty"}
  },
  "tracks": {
    "voice": "asset-id",
    "bed": "asset-id",
    "ambience": "asset-id",
    "effects": ["asset-id"]
  },
  "mix_targets": {
    "integrated_lufs_min": -16.0,
    "integrated_lufs_max": -14.0,
    "true_peak_dbtp_max": -1.0,
    "max_unmarked_silence_ms": 350,
    "ducking_db_min": 12,
    "ducking_db_max": 18
  },
  "caption_alignment": "word",
  "audio_planner_version": "audio-planner@1"
}
```

Utility voices set `public_eligible=false`. No later stage can override it.

## 9. Render manifest

```json
{
  "schema_version": "render-manifest.v2",
  "render_id": "sha256",
  "story_id": "sha256",
  "treatment_id": "sha256",
  "state": "candidate_rendered",
  "renderer": "remotion",
  "renderer_version": "pinned-version",
  "composition_version": "signal-forge-short@1",
  "video_path": "output/masters/.../master.mp4",
  "video_sha256": "sha256",
  "width": 1080,
  "height": 1920,
  "fps_num": 30,
  "fps_den": 1,
  "duration_ms": 38000,
  "audio_duration_ms": 37970,
  "preview": false,
  "watermarked": false,
  "input_hashes": {
    "beat_sheet": "sha256",
    "visual_plan": "sha256",
    "audio_plan": "sha256"
  },
  "resource_evidence": {
    "host_profile": "mac-mini-v1",
    "peak_rss_mb": 620,
    "wall_seconds": 93,
    "concurrent_media_jobs": 1
  }
}
```

Public-eligible requires 1080x1920, 30 fps, `preview=false`,
`watermarked=false`, eligible voice, and peak resources inside the selected host
profile.

## 10. Creative report and arbiter decision

```json
{
  "schema_version": "creative-report.v2",
  "render_id": "sha256",
  "spec_version": "2.0",
  "revision": 0,
  "deterministic_checks": {
    "rights": {"passed": true, "evidence": ["asset-id"]},
    "sync": {"passed": true, "delta_ms": 30},
    "caption_coverage": {"passed": true, "ratio": 1.0},
    "text_bounds": {"passed": true, "violations": []},
    "visual_density": {"passed": true, "shot_count": 11},
    "placeholder_scan": {"passed": true, "matches": []},
    "audio_mix": {"passed": true, "integrated_lufs": -14.8},
    "back_transcription": {"passed": true, "word_error_rate": 0.03}
  },
  "critic": {
    "model_id": "local-model@pinned-version",
    "prompt_version": "creative-critic@1",
    "scores": {
      "attention": 92,
      "story": 88,
      "visual": 90,
      "polish": 86,
      "trust": 100
    },
    "evidence": [
      {"criterion": "promise_by_2500ms", "passed": true, "frame_ids": [45], "reason": "..."}
    ]
  },
  "evidence_verifier": {
    "passed": true,
    "unresolved_criteria": []
  },
  "decision": "pass",
  "failure_codes": [],
  "targeted_revision": null,
  "arbiter_version": "release-arbiter@1"
}
```

Arbiter thresholds:

- Every deterministic check passes.
- Trust score equals 100.
- Attention, story, visual, and polish each score at least 85.
- Evidence verifier passes every required criterion.
- Revision is 0, 1, or 2.
- The critic model/prompt differs from the producing model/prompt.
- A score without timestamp, frame, asset, or transcript evidence is invalid.

Decision is one of `pass`, `revise`, or `hold`. A third failed candidate always
becomes `hold`.

## 11. Production job state machine

Allowed forward path:

```text
discovered
  -> rights_verified
  -> admitted
  -> scripted
  -> visual_planned
  -> assets_ready
  -> audio_ready
  -> preview_rendered
  -> candidate_rendered
  -> technical_passed
  -> arbiter_passed
  -> private_uploaded
  -> scheduled
  -> public
  -> analytics_24h_collected
  -> analytics_7d_collected
  -> archived
```

Terminal/side states:

- `rejected`: hard gate or score failed; new source content is required.
- `held`: creative revision limit reached; a new treatment version is required.
- `retryable_failure`: transient API, host, network, or renderer failure.
- `blocked_resource`: host ceiling exceeded; host profile or render plan must change.
- `cancelled`: explicit operator cancellation; no automatic resume.

Transition event:

```json
{
  "event_id": "sha256(previous_event_id + state + evidence_sha256)",
  "job_id": "sha256",
  "from_state": "technical_passed",
  "to_state": "arbiter_passed",
  "occurred_at": "2026-09-02T00:00:00Z",
  "evidence_refs": ["creative-report-sha256"],
  "attempt": 1,
  "actor": "release-arbiter@1"
}
```

Rules:

- Events append; historical events are never rewritten.
- A worker acquires a job lease with expiration before side effects.
- State and evidence are committed atomically.
- A retry uses the same idempotency key.
- Upload is allowed only from `arbiter_passed`.
- Public/scheduled upload is impossible for previews or missing arbiter evidence.
- TikTok has no transition in v2.
- Analytics absence is `unavailable` or pending, never numeric zero.

## 12. Revision contract

Targeted revision contains exactly one primary failure domain:

```json
{
  "domain": "opening|story|visual|voice|caption|mix|trust|technical",
  "target_ids": ["beat-id", "shot-id"],
  "observed_evidence": ["frame-45", "timestamp-1800"],
  "required_change": "specific measurable change",
  "preserve": ["claim-ids", "passed-criteria"],
  "new_treatment_version": 2
}
```

Revision may change only the named domain and dependent timing. It must preserve
source claims, rights, prior passed gates, and the original experiment variable.

## 13. Batch record

```json
{
  "schema_version": "batch.v2",
  "batch_id": "2026-W36-A",
  "story_ids": ["five unique ids"],
  "lane_mix": {
    "technical_catastrophe_or_hidden_dependency": 2,
    "impossible_build": 1,
    "obvious_fix_fails_or_human_vs_automation": 1,
    "wildcard": 1
  },
  "experiment": {
    "variable": "opening_type",
    "control": "consequence_first",
    "treatment": "result_first"
  },
  "status": "producing",
  "created_at": "2026-09-02T00:00:00Z"
}
```

Five videos do not become a batch merely by sharing a date. The lane mix and
single experiment variable are required.

## 14. Core function boundaries

```python
def verifySource(rawSource: RawSource) -> SourceRecord: ...
def scoreStory(source: SourceRecord) -> StoryAdmission: ...
def attachDemand(admission: StoryAdmission, packet: DemandPacket | None) -> RankedStory: ...
def compileBeats(story: RankedStory, treatment: Treatment) -> BeatSheet: ...
def planVisuals(source: SourceRecord, beats: BeatSheet, assets: AssetIndex) -> VisualPlan: ...
def planAudio(beats: BeatSheet, providers: ProviderRegistry) -> AudioPlan: ...
def renderCandidate(job: ProductionJob, inputs: RenderInputs) -> RenderManifest: ...
def assessTechnical(manifest: RenderManifest) -> TechnicalReport: ...
def arbitrateRelease(packet: ArbiterPacket) -> CreativeReport: ...
def transition(job: ProductionJob, event: TransitionEvent) -> ProductionJob: ...
```

Each function validates input schema/version, returns a new value, and raises a
typed boundary error. It never prints secrets, silently substitutes a provider,
or performs an undeclared platform side effect.
