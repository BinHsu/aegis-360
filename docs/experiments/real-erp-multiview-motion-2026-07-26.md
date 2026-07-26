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

## Fixed leave-one-view-out diagnosis

The same interval was repeated once more. The production all-ray fit remained
unchanged, while each pair also computed six diagnostic fits, each omitting
one viewport. Artifact root relative output:
`outputs/source-motion/old-ghost-road-25-30-fps25-leave-one-out-v3/`.

| Omitted view | Accepted pairs | Accepted fraction | Residual / step failures | Median / p95 residual |
| --- | ---: | ---: | ---: | ---: |
| back | 66 | 53.2% | 43 / 15 | 0.967° / 1.412° |
| down | 54 | 43.5% | 56 / 14 | 1.032° / 1.532° |
| left | 34 | 27.4% | 79 / 11 | 1.065° / 1.503° |
| up | 16 | 12.9% | 86 / 22 | 1.180° / 1.581° |
| front | 13 | 10.5% | 100 / 11 | 1.181° / 1.654° |
| right | 12 | 9.7% | 95 / 17 | 1.178° / 1.545° |

The unchanged six-view baseline again accepted 23/124 pairs. Omitting back
or down therefore produces a real but incomplete improvement, while omitting
front, right, or up makes acceptance worse. This corroborates the spatial
asymmetry seen in the per-view fits, but 46.8% of pairs still fail even in
the best fixed omission. A global five-view rig is not justified by one
interval, and a fixed omission cannot respond when the unreliable region
moves with scene content.

This diagnostic took 156.76 seconds because it performed six additional
robust fits per pair. Maximum child RSS was 283,754,496 bytes; swap decreased
by 8 MB and macOS recorded no thermal or performance warning.

The next bounded experiment should perform per-pair view-level consensus:
select a subset using a declared, deterministic disagreement criterion,
retain at least four views, and compare it with both the six-view baseline
and all six fixed omissions. Selection must not use the final acceptance
label as an oracle. Validate the selector on synthetic corrupted-view cases
before another real-media run.

## Rotation-medoid consensus diagnosis

A deterministic selector was implemented and validated before the real run.
It chooses the per-pair rotation medoid, retains every view within 1° of that
medoid, and requires at least four retained views. The radius equals the
unchanged fit-residual bound; selection never inspects the selected fit's
acceptance result. Synthetic tests reject one corrupted view, fail closed on
a 3-versus-3 split, and preserve deterministic tie-breaking. The complete
synthetic ERP/Vision gate also passes.

Artifact root relative output:
`outputs/source-motion/old-ghost-road-25-30-fps25-consensus-v4/`.

| Metric | Six-view baseline | Rotation-medoid consensus |
| --- | ---: | ---: |
| Accepted pairs | 23/124 | 36/124 |
| Accepted fraction | 18.5% | 29.0% |
| Insufficient-consensus failures | n/a | 88 |
| Selected-view count, 1 / 2 / 3 / 4 / 5 | n/a | 15 / 25 / 48 / 35 / 1 |
| Median / p95 residual of fitted subsets | 1.115° / 1.551° | 0.585° / 0.885° |

Every subset that retained at least four views passed the existing step,
confidence, inlier, and residual gates. The limiting factor was coverage:
88 pairs had only one to three views inside the predeclared radius. Rejection
counts were back 121, down 101, left 90, right 31, up 26, and front 21.

The selector improves on all-six fusion but underperforms the best fixed
omissions (66 pairs without back and 54 without down). Do not widen the 1°
radius after observing this run: that would tune on the evaluation interval
and could merely reintroduce incompatible views. The evidence instead says
that one compact medoid ball is too brittle for this scene.

The run took 61.65 seconds, maximum child RSS was 283,115,520 bytes, swap was
unchanged, and macOS recorded no thermal or performance warning.

Before another real run, define and test a selector that can distinguish
spatially coherent parallax from camera rotation without tuning against this
interval. Candidate evidence includes temporal reliability priors learned
only from preceding pairs, foreground/near-field exclusion, or a robust
view-level estimator that weights consensus continuously rather than using a
hard radius. The current medoid selector remains a negative baseline.

## Temporally causal reliability diagnosis

A second selector ranks each current pair using only earlier-pair evidence.
After an all-six-view first pair, it selects the four viewports with the
lowest EWMA of prior rotation-medoid disagreement. The update alpha is
predeclared as 0.2, an effective window of roughly five observations. The
current pair updates reliability only after its subset and fit are complete,
so a current failure cannot improve its own selection.

Unit tests prove past-only selection, deterministic ranking, and bounded EWMA
updates. The full synthetic ERP/Vision gate passes. Artifact root relative
output:
`outputs/source-motion/old-ghost-road-25-30-fps25-causal-v5/`.

| Metric | Six-view | Hard medoid | Causal reliability |
| --- | ---: | ---: | ---: |
| Accepted pairs | 23/124 | 36/124 | 86/124 |
| Accepted fraction | 18.5% | 29.0% | 69.4% |
| Residual failures | 90 | 0 after subset formed | 23 |
| Step failures | 11 | 0 after subset formed | 15 |

Viewport selection counts over 124 pairs were front 124, up 120, right 119,
left 97, down 35, and back 3. This is stronger than the best fixed omission
(66/124 without back), supporting a time-varying reliability policy.

Failures are not uniformly distributed. The first 23 pairs form one
0.92-second invalid run. After that initial burst, 86/101 pairs pass (85.1%);
the remaining fifteen failures form nine runs: five of one frame, two of two
frames, and two of three frames. Thus the post-burst maximum gap is 0.12
seconds at 25 fps. Do not hide the initial burst in the aggregate score.

The run took 66.29 seconds, maximum child RSS was 282,148,864 bytes, swap was
unchanged, and macOS recorded no thermal or performance warning.

This result justifies making causal pair rotations explicit in a separate
analysis artifact and evaluating a declared gap policy. It does not yet
justify rendering: the current production source-motion output still uses
the unchanged six-view baseline, causal diagnostic rows do not yet persist
their fitted quaternion, and neither the 0.92-second initial gap nor later
short-gap interpolation has been validated for visual comfort.

The same configuration was rerun after adding
`aegis360.causal-rotation-steps.v1`. The v6 artifact contains 124 local pair
steps: 86 measured steps each have one quaternion, while all 38 invalid steps
have `rotation_xyzw: null`. It contains no pixels, identity data, source path,
or absolute local path. Results reproduce v5 exactly. The artifact is under
`outputs/source-motion/old-ghost-road-25-30-fps25-causal-steps-v6/`.

This is deliberately not named source motion: local rotation steps separated
by gaps do not yet form a connected absolute orientation path.

## Gap-policy classification

A versioned classify-only policy was applied to v6. Boundary gaps are always
unbridgeable. Interior runs of at most three frames are labeled
`bridge_candidate`, not filled. The 0.12-second bound is an explicit
pre-render hypothesis and not a viewer-comfort claim.

The result contains ten runs and 38 invalid steps:

- one unbridgeable boundary run containing the first 23 steps;
- nine interior bridge candidates containing the remaining 15 steps.

The privacy-safe result is under
`outputs/source-motion/old-ghost-road-25-30-fps25-causal-gap-policy-v1/`.
Its policy declares `performs_interpolation: false`.

The next gate is synthetic known-motion validation of a short-gap spherical
interpolator. It must continue to reject boundary gaps and must quantify
angular reconstruction error before being applied to real local steps.
