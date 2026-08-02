# Project status

Status: Detector-only tracklets fragment safely; seeded tracking is next

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
detector-only tracklets now work; a seeded tracker is needed for continuity.

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
- Tracking grace, termination, fresh-ID acquisition proposal, lifecycle-to-
  planner fallback and semantic planning have bounded unit/real evidence.

## Current limitations

- Raw detections include cross-viewport duplicates. The `up` view's 19 very
  large person boxes are suspect boundary/projection artifacts.
- No real benchmark result proves identity through occlusion, view handoff or
  ERP seam crossing. Detector geometry must not manufacture identity.
- Detector-only lifecycles are operational geometry, not verified identity or
  editorial persistence. None has entered planning or rendering.
- Interest signals still omit motion change, novelty, event importance and
  audio; the global planner is not implemented.
- This bounded 12.6-second execution is not evidence of sustained thermal
  behavior, real-time output, or zero swap.

## Active acceptance gate

After a mutual-unique acquisition, seed a bounded Vision tracker on the
corresponding rectilinear view. Use detector refresh plus existing lifecycle
rules to survive detector gaps while failing closed on multiple compatible
detections. A view exit is a handoff request, not proof of identity.

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
- Semantic planning gate: `docs/experiments/semantic-lifecycle-planning-gate-2026-08-02.md`
- Detector equivalence: `docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`
- Detector cadence: `docs/experiments/yolox-coreml-stream-cadence-2026-07-30.md`
- Rejected first render: `docs/experiments/first-auto-directed-slice.md`
- Operational checkpoint: `docs/handoff/current.md`
