# Project status

Status: Perception and planning integration is the active POC gate

## Current conclusion

The repository has an executable offline pipeline skeleton for monoscopic
equirectangular input: spherical geometry, bounded perception artifacts,
semantic detector adapters, Vision tracking probes, lifecycle-aware candidate
generation, an explainable greedy baseline, camera-path generation and
FFmpeg rendering. The global planner and a useful end-to-end auto-directed
result remain incomplete.

The first rendered auto-directed candidates were rejected by owner review.
Wider 110/120-degree framing did not materially reduce motion sickness.
Gyro-free source-motion experiments, spatial masks and independent tile
consensus also failed to beat fixed-forward on the bounded screen-space
motion proxy. For the POC, retain raw/fixed-forward treatment and do not spend
another milestone tuning stabilization thresholds.

## What is verified

- The public three-video benchmark manifest and licensing records exist;
  benchmark media and generated artifacts remain outside Git.
- FFmpeg `v360` geometry and renderer conventions pass synthetic gates.
- YOLOX-Tiny FLOAT32 Core ML conversion passes the frozen numerical
  equivalence contract. The external model is manifest-indexed.
- A load-once FFmpeg/Core ML detector stream preserves the formal decoder
  contract. A 180-second source workload at 4 fps processed 720 frames in
  15.680 seconds at 45.92 fps with about 384 MB peak RSS.
- A confirmed bicycle detection seeded a bounded Vision track. Refresh and
  lifecycle rules fail closed on ambiguity, terminate after bounded misses,
  never revive a terminated track and never promote geometric continuity to
  verified identity or editorial persistence.
- The planner removes a terminated subject and deterministically falls back
  to forward context.
- Group/context candidates and a bounded `group_coverage` signal exist, but
  their prior 30-second render did not produce a perceptible directing
  difference and is rejected.
- The current repository baseline passes 228 unit tests and the handoff
  contract on the reference machine.

## Current limitations

- No real benchmark result demonstrates subject identity through occlusion,
  cross-viewport handoff or an ERP seam crossing.
- The semantic detector has useful but incomplete person/bicycle coverage.
- Existing 30-second evidence was assembled from sparse or manually selected
  sequences rather than one integrated semantic analysis pass.
- No current plan produces materially differentiated renderer-visible shots
  that have passed owner review.
- Interest signals still omit motion change, scene novelty, event importance
  and audio; the global planner is not implemented.
- The optimized detector completed the 180-second source workload in 15.7
  wall seconds, so this is not a three-to-five-minute thermal-duration result.

## Active acceptance gate

Build the smallest planning-only semantic sequence that connects the existing
load-once YOLOX stream, detector refresh, Vision lifecycle and lifecycle-to-
candidate boundary over a longer bounded Old Ghost Road interval.

Before rendering, require all of the following:

1. Every selected subject has explicit semantic/lifecycle provenance.
2. Terminated tracks disappear no later than their terminal sample and cannot
   be revived under the old ID.
3. Forward or group context remains available through gaps.
4. The renderer-aware pose replay predicts a sustained, perceptible
   difference from fixed-forward without lowering the accepted switch margin
   merely to manufacture cuts.
5. The artifact remains path-free, bounded-memory and analysis-only.

If the gate cannot create meaningful viewpoint differentiation, investigate
candidate coverage and interest signals before rendering. Do not return to
stabilization tuning or prioritize a thermal loop while directing quality is
the blocking product risk.

## Evidence map

- Current architecture: `docs/design/system-overview.md`
- Perception and lifecycle rules: `docs/design/perception-and-tracking.md`
- Planner design: `docs/design/shot-planner.md`
- Rejected first render: `docs/experiments/first-auto-directed-slice.md`
- Source-motion evidence: `docs/experiments/real-erp-multiview-motion-2026-07-26.md`
- Detector conversion: `docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`
- Detector cadence/performance: `docs/experiments/yolox-coreml-stream-cadence-2026-07-30.md`
- Operational checkpoint: `docs/handoff/current.md`
