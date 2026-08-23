# Experiments

Status: Active index

Experiments answer feasibility questions; they do not silently establish
architecture decisions. Each record states its own execution status; an
experiment protocol is not evidence until it records an actual run. Record raw
artifacts under the configured external data root and commit only compact,
privacy-safe summaries when results exist.

## Experiment index

- `geometry-validation.md`: coordinate, seam, pole, FOV and interpolation
  correctness.
- `ffmpeg-v360-dynamic-path.md`: installed `v360` command semantics, quality,
  timestamps and iteration cost.
- `ffmpeg-v360-runtime-pose-regression-2026-07-23.md`: synthetic evidence that
  a single first-frame yaw update matches a static pose while repeated runtime
  yaw updates on FFmpeg 8.1.1 can become path-dependent.
- `perception-projection-comparison.md`: ERP versus overlapping viewport
  perception/tracking.
- `perception-review-annotations.md`: privacy-safe manual review schema for
  fixed-timestamp four-viewport perception evidence.
- `perception-environment-probe-2026-07-23.md`: installed runtimes and
  acceleration surfaces available for the first perception backend.
- `apple-vision-real-frame-gate-2026-07-23.md`: synthetic and Old Ghost Road
  single-frame Apple Vision bootstrap evidence.
- `apple-vision-review-pack-2026-07-23.md`: local-only fixed-sample contact
  sheets and privacy-safe index prepared for human candidate review.
- `apple-vision-tracking-gate-2026-07-23.md`: bounded synthetic and
  Old Ghost Road `VNTrackObjectRequest` continuity evidence.
- `apple-vision-tracking-batch-gate-2026-07-23.md`: manifest-driven,
  privacy-safe aggregation of several bounded tracking clips.
- `apple-coreml-semantic-detector-contract-2026-07-29.md`: acquired model,
  checksum, Core ML/Vision recognized-object and privacy-safe synthetic gate.
- `apple-coreml-semantic-detector-smoke-2026-07-29.md`: fixed-five
  multi-viewport natural-image person/bicycle seed evidence and visual audit.
- `coreml-seeded-vision-tracking-2026-07-29.md`: isolated versus crowded
  short-sequence box continuity and identity limitation.
- `native-detector-refresh-trace-2026-07-29.md`: viewport-aspect correction,
  exact-timestamp detector refresh and fail-closed visual audit.
- `yolox-coreml-stream-cadence-2026-07-30.md`: one FFmpeg raw-video stream,
  one Core ML model load, cadence decomposition and comparison with
  exact-timestamp process-per-frame refreshes.
- `yolox-multiview-semantic-events-2026-08-02.md`: privacy-safe six-view
  person/bicycle event schema and bounded 30-second Old Ghost Road acquisition
  evidence.
- `semantic-seeded-vision-lifecycle-2026-08-06.md`: automatic semantic
  acquisition-to-Vision seed, visual continuity audit, Core ML refresh and
  lifecycle integration on one bounded isolated person.
- `vision-face-composition-probe-2026-08-09.md`: stable face-based vertical
  composition evidence and the real-scene rejection of single-face framing.
- `apple-sound-reaction-gate-2026-08-15.md`: closed offline applause evidence,
  conservative reaction intervals, and live-scene availability limits.
- `smolvlm2-500m-context-gate-2026-08-11.md`: acquired MLX model, M4/16 GB
  feasibility and rejection after three closed-output protocols failed.
- `smolvlm2-2.2b-context-gate-2026-08-13.md`: constrained four-frame group
  selection across two sources, fixed-input repeatability, and a held-out
  landscape context-selection failure.
- `smolvlm2-2.2b-reaction-gain-gate-2026-08-15.md`: closed pairwise comparison
  rejection after the model abstained on both positive and negative cases.
- `event-timeline-v1-2026-08-16.md`: checksummed reaction-candidate timeline
  across two sources, with view availability but no imported editorial labels.
- `event-review-packet-v1-2026-08-16.md`: five-anchor sparse review manifests
  with boundary-aware context and availability-filtered candidate references.
- `transient-event-review-media-2026-08-16.md`: bounded silent frame rendering,
  adapter handoff, failure propagation and verified temporary-media cleanup.
- `ffmpeg-scene-change-events-2026-08-16.md`: privacy-safe scene-score peaks,
  visually rejected 4-second NMS, retained 10-second NMS and 5K VP9 limitation.
- `multi-signal-timeline-review-v2-2026-08-16.md`: neutral signal fusion,
  eight-frame cardinal review packets and verified transient-media cleanup.
- `scene-story-context-v1-2026-08-23.md`: multi-cadence boundary correction,
  bounded 30-second cardinal context and closed source-context story labels.
- `story-segment-view-relevance-v1-2026-08-23.md`: boundary-partitioned shot
  scopes, three-composite packets and observed/abstained candidate evidence.
- `semantic-lifecycle-planning-gate-2026-08-02.md`: multi-lifecycle candidate
  timeline, termination/fallback contract, renderer-aware planning-only pose
  differentiation and the forward-context FOV false-positive correction.
- `vision-spherical-dedup-wiring-2026-07-23.md`: fixed-five Vision JSON
  ingestion, spherical dedup report, and neutral perception-to-planner wiring.
- `planner-baselines.md`: fixed, greedy and global directing comparison.
- `m4-air-sustained-performance.md`: memory, swap, thermals and sustained
  throughput on the reference machine.
- `benchmark-projection-validation.md`: source/container/manual projection
  evidence and the per-asset accept-or-override gate.
- `duration-ladder-protocol.md`: nested 30/60/180/300-second comparison
  contract with per-asset eligibility and three required outputs.
- `first-auto-directed-slice.md`: first real-media vertical-slice gate from
  bounded Vision sequence evidence through greedy camera path and the three
  duration-ladder review artifacts.
- `rendered-flat-shake-probe-2026-07-23.md`: dependency-light paired
  screen-space translation/jitter protocol for fixed versus auto renders and
  leading versus trailing windows.
- `real-erp-multiview-motion-2026-07-26.md`: analysis-only Old Ghost Road
  25–30 second spherical source-motion evidence at bounded sampling rates.

## Required experiment record

Every run records question, decision unlocked, commit, configuration, hardware,
OS, FFmpeg, model/weights/checksum, input/hash, procedure, metrics, acceptance
criteria fixed before results, artifact locations, results, limitations,
conclusion and follow-up. Do not report a performance or quality claim without
the corresponding record. Acquisition is explicit; normal experiment commands
must not download assets.
