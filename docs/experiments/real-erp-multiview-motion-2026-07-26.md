# Real ERP multiview source-motion probe — 2026-07-26

Status: 12.5 fps, 25 fps, and per-view disagreement runs complete

## Question

Can the calibrated six-viewport Apple Vision pipeline produce enough valid
bounded `SO(3)` steps from five seconds of real first-person 360 footage to
justify source-path smoothing, without relaxing the synthetic fit gates?

## Decision unlocked

Determine whether temporal sampling is the immediate bottleneck or whether
real-scene parallax, moving foreground and cross-viewport inconsistency
dominate. Do not render a stabilized or viewer-review video from this
experiment.

## Implementation and environment

- Implementation commit: `f3c081d`
- Hardware: fanless Apple Silicon MacBook Air M4, 16 GB unified memory
- OS: macOS 26.5.2 arm64
- FFmpeg: 8.1.1
- Vision backend: `VNTrackHomographicImageRegistrationRequest`, revision 1
- Model weights: none
- Input: Old Ghost Road benchmark ERP, 4096x2048, 25 fps
- Interval: 25–30 seconds
- Artifact root relative output:
  `outputs/source-motion/old-ghost-road-25-30-fps12.5-v1/`

The committed benchmark manifest owns source identity, checksum and licensing.
No source path, frames or video are retained in the result artifact.

## Configuration

- ERP sample rate: 12.5 fps
- Viewports: front, right, back, left, up and down
- Viewport size: 640x360
- Horizontal FOV: 110°
- Maximum fitted step: 1.25°
- Minimum contributing viewports: 4
- Minimum fit confidence: 0.2
- Minimum inlier ratio: 0.5
- Maximum fit residual: 1°
- Homography sampling grid: 9x7 per contributing viewport

These are the existing bounded synthetic settings. The real-media run did not
change a threshold after seeing its output.

## Procedure

For each fixed viewport, the runner decoded clip-relative samples into a
private temporary directory, ran sequential Vision homographic registration,
converted Vision-native transforms to source-to-target top-left coordinates,
converted sampled pixel matches to world rays, robustly fit a fused `SO(3)`
step, and deleted the temporary frames. It retained only:

- `source-motion.json`
- `report.json`

The first command attempt expanded an inline environment variable before its
assignment and therefore did not find an input. A second attempt stopped
before output because the runner expected 62 rather than FFmpeg's 63 frames
for 5x12.5 samples. The runner was corrected to use a ceiling for fractional
sample counts; neither failed attempt produced a result directory.

## Results

All six viewport sequences returned 62/62 Vision motion observations with no
Vision error:

| Metric | Result |
| --- | ---: |
| Adjacent pairs | 62 |
| Accepted measured pairs | 2 |
| Invalid pairs | 60 |
| Measured fraction | 0.0323 |
| Residual-bound failures | 44 |
| Step-angle-bound failures | 16 |
| Median / p95 / max step angle | 0.816° / 1.848° / 2.246° |
| Median / p95 / max fit residual | 1.253° / 1.728° / 2.048° |
| Median fit confidence | 0.520 |
| Median inlier ratio | 0.893 |
| Contributing viewports | 6 for every pair |
| Elapsed wall time | 52.37 s |
| Maximum child-process RSS | 278,659,072 bytes |

At report time, system swap usage was 8,550.12 MB of 9,216 MB. This is an
absolute observation, not experiment-attributed swap growth, because the
runner did not capture a before value.

## Interpretation

12.5 fps is insufficient for this interval under the calibrated bounds. Only
27% of invalid pairs failed primarily on step angle; 73% failed on fused
residual. Every viewport produced an observation and every pair used all six
views, so simple Vision availability or declared viewport coverage is not the
immediate failure.

The residual distribution is consistent with, but does not prove, parallax,
moving bicycle/rider foreground, stitching artifacts or disagreement among
the independently fitted viewport homographies. Higher temporal sampling is
still justified because it reduces inter-frame displacement without changing
fit thresholds. If 25 fps does not materially reduce residual failures, the
next investigation should use per-view robust diagnostics and foreground
masking rather than threshold relaxation.

## Limitations

- Homography-derived motion is not camera-motion ground truth.
- The benchmark has no validated gyro orientation for comparison.
- The report did not record swap before and after the run.
- Maximum child RSS is not a complete system-memory or thermal measurement.
- Measured-pair fraction is not a viewer-comfort metric.
- No stabilization path `S(t)` or output video was produced.

## Conclusion and follow-up

Do not advance this 12.5 fps path to smoothing or rendering.

## Source-rate 25 fps comparison

The same interval was rerun at the source rate with no fit-threshold change.
Artifact root relative output:
`outputs/source-motion/old-ghost-road-25-30-fps25-v1/`.

| Metric | 12.5 fps | 25 fps |
| --- | ---: | ---: |
| Adjacent pairs | 62 | 124 |
| Accepted measured pairs | 2 | 23 |
| Measured fraction | 0.0323 | 0.1855 |
| Residual-bound failures | 44 | 90 |
| Step-angle-bound failures | 16 | 11 |
| Median step angle | 0.816° | 0.525° |
| p95 step angle | 1.848° | 1.388° |
| Median fit residual | 1.253° | 1.115° |
| p95 fit residual | 1.728° | 1.551° |
| Median fit confidence | 0.520 | 0.626 |
| Median inlier ratio | 0.893 | 0.996 |
| Elapsed wall time | 52.37 s | 74.80 s |
| Maximum child-process RSS | 278,659,072 B | 283,377,664 B |

The 25 fps run recorded 8,526.12 MB swap before and 8,502.12 MB after, so it
did not increase the already-high system swap observation. `pmset -g therm`
reported no recorded thermal or performance warning before or after. These
are bounded observations, not proof of long-duration thermal behavior.

Higher sampling reduced step-angle failures substantially and raised the
accepted fraction, but 81.5% of pairs remained invalid. Residual failures
still dominated. All six viewports returned 124/124 Vision observations, and
all were present in every fused pair. The down viewport's Vision affine
rotation proxy RMS was 0.150 radians, versus 0.014–0.025 for five other
viewports, making per-view disagreement a concrete next diagnostic.

Do not increase sampling beyond the 25 fps source rate or relax thresholds.
Persist bounded per-view fit angle, residual, confidence and agreement with
the fused rotation, then rerun this same interval to determine whether the
down view, foreground/parallax, or multiple views are responsible.

## Per-view rotation-fit diagnosis

The 25 fps run was repeated with identical input, interval, viewports, and
acceptance thresholds. Only privacy-safe per-view `SO(3)` fit summaries and
their angular distance from the all-ray fused rotation were added. Artifact
root relative output:
`outputs/source-motion/old-ghost-road-25-30-fps25-per-view-v2/`.

| View | Median step | Median fit residual | Median / p95 fused disagreement |
| --- | ---: | ---: | ---: |
| front | 0.763° | 0.267° | 0.444° / 1.465° |
| right | 0.630° | 0.208° | 0.500° / 2.256° |
| up | 0.681° | 0.210° | 0.521° / 1.070° |
| left | 1.396° | 0.839° | 1.099° / 2.170° |
| down | 1.823° | 0.563° | 1.506° / 2.749° |
| back | 1.978° | 0.898° | 1.883° / 3.238° |

Every view produced 124/124 per-view fits. The fused outcome reproduced the
prior run exactly: 23 measured pairs, 90 residual failures, and 11 step-bound
failures. The run took 83.25 seconds, maximum child RSS was 285,294,592
bytes, swap was unchanged at 8,422.12 MB, and macOS recorded no thermal or
performance warning.

The earlier down-view affine rotation-proxy RMS outlier does not identify a
single removable culprit. In spherical fits, back, down, and left all
systematically report larger motion and disagree more strongly with the
all-ray fused rotation than front, right, and up. The up view also has one
rare 9.53° disagreement maximum despite its low p95. This pattern is
consistent with spatially varying motion evidence such as near-field
bicycle/rider parallax, blur, or stitching behavior; without ground truth it
does not prove which cause dominates.

Do not relax the fused residual gate and do not discard only the down view.
The next bounded estimator experiment should compare robust view-level
consensus or leave-one-view-out fits and record which views are rejected for
each pair. That experiment must first pass synthetic geometry and must retain
the current all-ray fusion as its baseline.
