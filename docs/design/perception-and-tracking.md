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

## Acceptance criteria

On annotated benchmark excerpts, compare candidate recall, duplicate rate,
track fragmentation, identity switches, seam continuity, elapsed time and peak
memory. The chosen strategy must enable useful directing on the reference
machine; maximum detector accuracy is not itself the goal.
