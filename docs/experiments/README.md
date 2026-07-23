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

## Required experiment record

Every run records question, decision unlocked, commit, configuration, hardware,
OS, FFmpeg, model/weights/checksum, input/hash, procedure, metrics, acceptance
criteria fixed before results, artifact locations, results, limitations,
conclusion and follow-up. Do not report a performance or quality claim without
the corresponding record. Acquisition is explicit; normal experiment commands
must not download assets.
