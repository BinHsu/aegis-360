# Real ERP multiview source-motion probe — 2026-07-26

Status: 12.5 fps run complete; 25 fps comparison pending

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

Do not advance this 12.5 fps path to smoothing or rendering. Run the identical
25–30 second interval at the source rate of 25 fps with unchanged motion and
fit thresholds, add before/after swap observations, and compare failure
reasons, residuals, step angles, elapsed time and memory.
