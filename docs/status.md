# Project status

Status: Conversation-group composition accepted; bounded group gate under test

## Current conclusion

The repository has an executable offline pipeline skeleton for monoscopic
equirectangular input: spherical geometry, bounded perception artifacts,
semantic detector adapters, tracking/lifecycle rules, an explainable greedy
baseline, camera-path generation and FFmpeg rendering. The global planner and
a useful end-to-end auto-directed result remain incomplete.

The first rendered auto-directed candidates were rejected by owner review.
Wider framing and gyro-free source-motion variants did not materially improve
comfort. A later bicycle plan created visible camera differentiation, but
agent review rejected its near-field/ego-equipment subject before owner review.

The blocking risk was semantic coverage rather than rendering. A new six-view
30-second Old Ghost Road run now shows that load-once YOLOX/Core ML acquisition
can expose sustained people around the camera while remaining fast and bounded
on the M4/16 GB reference machine. These are detector events, not identities or
editorial candidates. Same-timestamp spherical merging and conservative
detector-only tracklets work, and one mutual-unique acquisition now seeds a
visually verified native track with compatible detector refresh throughout.

## What is verified

- Public benchmark provenance and licensing records exist; media, models and
  generated artifacts remain outside Git.
- FFmpeg `v360` geometry and renderer conventions pass synthetic gates.
- YOLOX-Tiny FLOAT32 Core ML conversion passes frozen numerical equivalence.
- `aegis360.semantic-detector-events.v2` is deterministic, path-free,
  privacy-safe, person/bicycle-only, geometry-bounded and pre-identity.
- V2 includes viewport pixel dimensions, making normalized-box-to-ray
  conversion self-contained. V1 is rejected because it omitted aspect ratio.
- The multi-view runner loads Core ML once, processes six FFmpeg raw-BGR
  streams serially, writes atomically and refuses overwrite.
- Old Ghost Road 60–90 seconds produced all 720 expected event rows at 4 fps
  per view in 12.614 seconds with 365,527,040-byte peak RSS: 238 accepted
  person boxes, 17 bicycle boxes and 25 fail-closed geometry rejections.
- Detection-bearing samples span 95/120 timestamps and several headings.
  Agent contact-sheet inspection confirms real non-ego people across the
  interval and broader coverage than the earlier isolated bicycle lifecycle.
- Existing viewport-ray geometry converts v2 observations to spherical
  centers/extents. Same-time dedup reduces 255 observations to 240 clusters;
  15 clusters have two source views and none has more than two.
- A nonidentity geometric diagnostic finds a stable right-view person from
  67.75 through 78.75 seconds. An earlier down-to-right chain contains a jump,
  so it is not accepted as identity continuity.
- A tunable 0.9 normalized width/height framing gate quarantines 32/255 boxes
  as unsuitable for isolated subject framing, including all 19 suspect `up`
  boxes. It does not label them detector false positives.
- Mutual-unique 12-degree tracklets require two confirmations over 0.25
  seconds and two-sample grace. The real run creates 18 fresh IDs and 15
  terminations; 24/120 samples contain ambiguity. The longest outdoor person
  segment is about 4.0 seconds and the longest ending indoor segment 3.25
  seconds. Ambiguity fragments rather than nearest-neighbor swapping.
- A path-free seed manifest automatically carries the selected viewport,
  top-left-to-bottom-left box conversion, dimensions, yaw, pitch and FOV into
  the Vision runner. Nonzero-pitch views are supported by the runner contract.
- On Old Ghost Road 68.5–72.5 seconds, the manifest-seeded right-view person
  tracked 16/16 frames with zero loss/error and 1.500729-degree maximum center
  step. Five representative overlays retain the same blue-jacketed person.
- All 16 Core ML refreshes contain exactly one compatible person. The lifecycle
  remains active, consumes every event and still denies identity/editorial
  persistence.
- The unchanged greedy config selects this person 16/16 times. Correct
  separation of 19.664-degree subject extent from output FOV fixes a discovered
  130-degree over-wide render; the accepted render uses 110 degrees.
- Corrected fixed/auto 1080p peers pass the mechanical gate, but owner review
  rejects the directing result. For speaking-person framing, fixed needs to
  move right/down and auto needs to move up; centering one whole-body person
  box is not the correct composition.
- Semantic planning can now be rendered into one atomic, refuse-overwrite
  bundle without manually copying trace, config or camera-path artifacts.
- A translation-only shake proxy reports zero median/p95 motion for both peers;
  it does not establish comfort, roll stability or viewer preference.
- The bounded face probe finds one stable right-view face in all 16 samples at
  about pitch -6 degrees, versus -28 degrees for the whole-body track. This
  validates the owner's upward correction but misses another visible group
  member, so single-face framing is rejected.
- Tracking grace, termination, fresh-ID acquisition proposal, lifecycle-to-
  planner fallback and semantic planning have bounded unit/real evidence.

## Current limitations

- Raw detections include cross-viewport duplicates. The `up` view's 19 very
  large person boxes are suspect boundary/projection artifacts.
- No real benchmark result proves identity through occlusion, view handoff or
  ERP seam crossing. Detector geometry must not manufacture identity.
- The accepted lifecycle/render remains one isolated, single-viewport example
  and proves no exit, seam, occlusion or handoff.
- Interest signals still omit motion change, novelty, event importance and
  audio; the global planner is not implemented.
- This bounded 12.6-second execution is not evidence of sustained thermal
  behavior, real-time output, or zero swap.

## Active acceptance gate

Form a conversation/group candidate from person coverage, using face evidence
only to correct its visual center upward. Define a bounded short-window VLM
contract for scene context; keep camera geometry and planning deterministic.
Stereo audio availability does not prove direction or active-speaker identity.

The closed `aegis360.scene-context.v2` contract lets human or local-VLM evidence
select a geometry-declared person/group/context proposal with matching scope.
Group membership is declared before review and remains nonidentity. V1 is
rejected because it let review compose fragmented cross-time person IDs. The
contract cannot emit camera geometry, free text, identity or unchecksummed
model provenance.

At 8/16 samples, two simultaneous person detections form a stable group near
yaw 54 degrees. Face anchoring shifts its pitch from about -25 to -6 degrees
without changing membership or FOV. The missing second-person detections in
the other eight samples are now bridged only when explicit group context and a
0.5 observation floor are both present. The window result is nonidentity and
retains the renderer's independent minimum-FOV guard.

Window geometry now declares two proposal-local member slots plus one group
proposal. Slots carry no cross-time identity. A real unchanged-config replay
selects the group 16/16 times.

The geometry proposal, human/local-VLM selection handoff and planner adapter
are now separate atomic, path-free artifacts. A face-centered proposal at
pitch -6.124 degrees passed mechanical checks but failed agent review because
one detected face pulled the group too high. A conservative proposal limits
face correction to 5 degrees and renders at yaw 54.083, pitch -20.278 and HFOV
110 degrees. It passes the mechanical gate and agent contact-sheet review; the
owner accepts it as successfully capturing the two people in conversation.
This is a bounded group-framing pass, not active-speaker or identity evidence.
A later view exit remains a handoff request, not proof of identity.

A generic local-VLM importer now fail-closes on any model output containing
extra fields, invented candidate IDs or geometry. It verifies the exact model
asset SHA-256 and atomically emits scene-context v2; uncertain-with-no-selection
is valid. No backend/model has been selected or run, so this is an integration
boundary rather than automatic context-classification evidence.

SmolVLM2 500M Video MLX BF16 was explicitly acquired and is hardware-feasible
for the bounded four-frame run: 8.39 seconds, about 2.44 GB maximum RSS and zero
swap. It is rejected for planner integration: three prompt-only protocols
failed, while two grammar-constrained runs produced valid syntax but wrong
semantics or an invalid scope/candidate pair. Do not weaken the importer or
continue tuning this 500M model.

SmolVLM2 2.2B MLX BF16 is acquired and passes the bounded group-proposal gate.
The formal four-frame run selects `group:window:1`, takes 25.05 seconds model
elapsed, uses 6.97 GB MLX peak memory and no swap. Fine context class is not
accepted: repeated runs differed between `conversation` and `ambient_people`.
Use it only for bounded group-vs-not-group decisions, with the closed validator
retained; it has not passed context or person selection.

Two further formal runs on the identical four frame bytes reproduced the full
retained decision, including `group:window:1`, in 24.75 and 25.15 seconds at a
6.97 GB MLX peak. This supports fixed-input repeatability only; it does not
raise the evidence to cross-scene accuracy or make the fine class acceptable.

A separate manually screened non-group window declares no group proposal. The
2.2B runner returns uncertain/no-selection with all visual flags unknown rather
than inventing a group. This disproves an always-group behavior on one negative
window; it is not a general accuracy claim.

A second positive from Bellpuig contains four or more motocross riders racing
across all four samples. The runner selects the group proposal in 25.80 seconds
at the same 6.97 GB peak, extending the bounded group result across sources and
activity types. Its mouth-motion, reciprocal-orientation and fine-class output
are visibly wrong, so evidence flags and context class remain unusable.

A Skiing landscape window with only `context:forward` returns uncertain with
no selection in 24.91 seconds. This is safe refusal but fails the context gate.
The 2.2B model is not a generic proposal selector: accept only its bounded
group-vs-not-group behavior when geometry already supplies a group proposal.

Planner integration treats valid `uncertain`/null output as abstention. It
exposes only deterministic `context:forward`, records that resolution in the
trace, and keeps pose differentiation false when output matches fixed-forward.
Other non-group scope/candidate combinations still fail closed. A subprocess
contract test needs no external assets; symmetric cases assert 4/4 fallback
with a false pose gate and 4/4 selected group with a true pose gate.

Do not render until at least one candidate:

1. has explicit detector, spherical-merge and lifecycle provenance;
2. remains active long enough to survive the existing switch hold/margin;
3. is visually credible non-ego content rather than near-field equipment or a
   projection artifact; and
4. creates a renderer-visible pose difference without score tuning from this
   one excerpt.

## Evidence map

- Current architecture: `docs/design/system-overview.md`
- Perception and lifecycle rules: `docs/design/perception-and-tracking.md`
- Multi-view acquisition: `docs/experiments/yolox-multiview-semantic-events-2026-08-02.md`
- Seeded tracking/lifecycle: `docs/experiments/semantic-seeded-vision-lifecycle-2026-08-06.md`
- Semantic planning gate: `docs/experiments/semantic-lifecycle-planning-gate-2026-08-02.md`
- Detector equivalence: `docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`
- Detector cadence: `docs/experiments/yolox-coreml-stream-cadence-2026-07-30.md`
- Rejected first render: `docs/experiments/first-auto-directed-slice.md`
- Operational checkpoint: `docs/handoff/current.md`
