# Perception and tracking

Status: Design hypothesis pending projection comparison

## Responsibility

Perception discovers people, objects, motion/event regions and contextual
views. Tracking associates observations through time and across the ERP seam.
Neither layer decides what the viewer should watch.

Implement detector and tracker adapters with explicit model/weight identity,
input projection, timestamps, confidence and output coordinate space. The POC
may start with an available Ultralytics backend; no downstream schema may
depend on it.

## Candidate projection strategies

1. Downscaled ERP inference: fastest baseline, with severe seam/pole
   distortion risk.
2. Overlapping rectilinear viewports: less distortion, more inference and
   duplicate-merging cost.
3. Hybrid ERP proposals followed by selected viewport refinement.

No strategy is selected before the projection experiment. Cube faces are an
optional comparison only if the first two fail acceptance criteria.

## Identity rules

- A temporal ID is not automatically an identity. Every association records
  whether it came from explicit tracker identity, a human rectangle associated
  geometrically, generic geometry only, or synthetic context.
- Nearest-neighbor association of attention/objectness saliency is useful for
  continuity and deduplication, but cannot earn editorial persistence. Human
  rectangles may earn it as the bounded POC exception; any other candidate
  requires an explicit upstream tracker ID.
- Explicit tracker IDs are continued by exact ID, never silently reassigned by
  nearest geometry. This policy is expressed in the core schema and is
  independent of detector/tracker vendor or backend.
- Track positions are stored as unit directions plus optional spherical
  extents, never solely as planar ERP boxes.
- Duplicate observations in overlapping viewports are merged by spherical
  overlap/appearance evidence with provenance retained.
- Seam crossings must preserve identity through yaw wrapping.
- Lost tracks retain a bounded grace interval; confidence decays explicitly.
- Re-identification embeddings, if used, are ephemeral sensitive artifacts.

## POC outputs

Timestamped observations, tracks, confidence, class, direction/extent,
projection provenance and optional low-dimensional motion evidence. Outputs
must be cacheable independently of the planner.

The executable core contract is `src/aegis360/perception.py`. A frame sample
contains privacy-safe source and decode metadata, while an adapter returns
model-independent spherical candidates and named normalized evidence. Missing
signals carry an explicit reason. Adapter/backend/projection provenance is
retained, and model weights are identified by checksum when present.

Editorial weights are deliberately absent from adapter outputs. An explicit
`ScoringConfig` converts selected evidence into the greedy baseline's
`CandidateObservation`; unselected evidence remains in the cacheable
perception result. The current tests use only a synthetic no-model adapter and
do not establish real detector or tracker quality.

`src/aegis360/spherical_dedup.py` provides dependency-free Apple Vision gate
v1 ingestion and cross-viewport duplicate clustering. Rows for the same
source, frame and timestamp are combined first. Candidates merge only when
their kinds match and their great-circle center distance is within both a
configured absolute limit and an extent-derived limit. Boundary comparison
is inclusive and IDs provide deterministic ordering. Every original
candidate remains in the returned cluster; merged evidence retains all
duplicate-source and observation provenance.

The merge rule has no confidence threshold or confidence ordering. Detector
confidence remains named perception evidence, not editorial interest. Merged
geometry uses an equal-weight spherical mean and maximum member horizontal
extent. Merged signals are intentionally empty because combining backend
scores is a separate calibration question.

`tools/vision_tracking_gate.swift` is a bounded evidence probe for Apple's
OS-provided `VNTrackObjectRequest`. It accepts an externally supplied initial
box and a short ordered rectilinear frame sequence. It records a job-safe track
ID, box continuity, confidence as perception evidence, approximate spherical
centers, great-circle center steps, seam crossings, lost frames and privacy-
safe errors. It does not detect a subject, infer identity or score interest.
The single-viewport probe cannot continue a target after it leaves that
viewport; cross-viewport handoff remains a separate tracker-adapter problem.

`src/aegis360/tracking_policy.py` makes the minimum lost-track lifecycle
executable without choosing a tracking backend. Upstream code must classify
each expected sample as observed, not observed, or outside the current
viewport. The policy applies separately configurable frame-count grace
intervals, explicit confidence decay, and distinct termination reasons for a
missing timeout and a viewport-exit timeout. A new observation within grace
restores the active state; a terminated lifecycle cannot be revived implicitly.

The viewport-exit state is only a request boundary for a future handoff
adapter. It does not search another viewport, associate identities, or prove
ERP-seam continuity. Whether a box is outside the viewport is likewise an
upstream geometry decision, not inferred by this core policy.

`candidate_sequence.AssociationProvenance` is the executable validity policy.
`observed_frames` remains a diagnostic continuity count for every association,
but `interest.candidate_interest` converts it to nonzero persistence only when
`editorial_persistence_valid` is true. Detector confidence is not consulted by
association validity, identity continuation, or editorial interest.

## Acceptance criteria

On annotated benchmark excerpts, compare candidate recall, duplicate rate,
track fragmentation, identity switches, seam continuity, elapsed time and peak
memory. The chosen strategy must enable useful directing on the reference
machine; maximum detector accuracy is not itself the goal.
