# Current handoff

Updated: 2026-07-27T06:24:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 67c9c40
Remote status: main matches origin/main at this checkpoint
Working tree at checkpoint: owner rejected canonical; spatial residual diagnosis is active

## Objective

Build an offline, camera-agnostic 360-video auto-director. The current
technical objective is gyro-free spherical source-motion estimation before
another real-media stabilization or viewer-review candidate.

## Last completed milestone

The bounded six-viewport synthetic ERP runner was implemented at commit
`4b76cb6`. It converts Apple Vision registrations into world-ray
correspondences, robustly fits `SO(3)`, accumulates a privacy-safe source-motion
path, and fails closed on configured motion or fit-quality bounds.

The owner ran the host-only gate after increasing temporal sampling. All six
samples were `measured`, all residuals were finite, and the command reported:

```text
PASS: bounded synthetic ERP multiview Vision source-motion gate
```

The first real-media analysis-only run covered Old Ghost Road 25–30 seconds
at 12.5 fps. All six viewport Vision sequences returned 62/62 observations,
but the fused gate accepted only 2/62 pairs (3.2%): 44 exceeded the 1°
residual bound and 16 exceeded the 1.25° step bound. No viewer video was
rendered.

The unchanged-bound 25 fps comparison accepted 23/124 pairs (18.5%).
Step-angle failures fell from sixteen to eleven, but residual failures
increased with pair count to ninety and remained dominant. The down
viewport's affine rotation-proxy RMS was a clear outlier.

The repeated 25 fps run with per-view spherical diagnostics reproduced the
same 23/124 fused acceptance result. Disagreement is not confined to down:
back, down, and left have median fused disagreement of 1.883°, 1.506°, and
1.099°, versus 0.444–0.521° for front, right, and up.

The fixed leave-one-out run accepted 66/124 pairs without back and 54/124
without down, versus 23/124 for all six views. Omitting front, right, or up
reduced acceptance. The best fixed omission still failed 58 pairs.

The predeclared 1° rotation-medoid selector accepted 36/124 pairs. Every
four-or-more-view subset passed the existing fit bounds, but 88 pairs failed
as insufficient consensus. It improves on all-six fusion but underperforms
fixed omission of back or down.

The past-only EWMA reliability selector accepted 86/124 pairs (69.4%).
Failures include an initial 23-pair/0.92-second burst. After that burst,
86/101 pass and the longest later gap is three frames/0.12 seconds.

## Repository state

- Expected branch: `main`.
- Baseline commit: `67c9c40`.
- Commit `b98b64d` contains the handoff contract, validator, tests and CI
  enforcement. It and the bounded ERP runner were pushed to `origin/main`
  before this checkpoint metadata update.
- Commits through `67c9c40` are signed and pushed to `origin/main`.
- Media and generated video remain outside Git under the configured artifact
  root.

## Verified

- `python3 -m unittest discover -s tests -v`
  - PASS: 152 tests including privacy-safe spatial residual aggregation.
- `python3 -m unittest tests.test_handoff_contract -v`
  - PASS: 3 tests.
- `python3 scripts/check_handoff.py`
  - PASS.
- `tests/test_synthetic_erp_multiview_motion_gate.sh`
  - PASS on the owner's macOS host.
  - Six source-motion samples were measured with no invalid state.
- The 0.5° strict configuration in the same gate fails closed as
  `rotation_step_exceeds_configured_bound`.
- Real 12.5 fps analysis:
  - 62 pairs, 2 measured, 60 invalid.
  - Median/p95 step angle: 0.816° / 1.848°.
  - Median/p95 fit residual: 1.253° / 1.728°.
  - Elapsed: 52.37 seconds; maximum child RSS: 278,659,072 bytes.
- Real 25 fps analysis:
  - 124 pairs, 23 measured, 101 invalid.
  - Median/p95 step angle: 0.525° / 1.388°.
  - Median/p95 fit residual: 1.115° / 1.551°.
  - Elapsed: 74.80 seconds; maximum child RSS: 283,377,664 bytes.
  - Swap changed from 8,526.12 MB to 8,502.12 MB; no recorded thermal warning.
- Per-view 25 fps diagnosis:
  - Reproduced 23 measured, 101 invalid, 90 residual failures, and 11
    step-bound failures.
  - All six viewports produced 124/124 spherical fits.
  - Median/p95 fused disagreement: back 1.883°/3.238°, down
    1.506°/2.749°, left 1.099°/2.170°, front 0.444°/1.465°, right
    0.500°/2.256°, up 0.521°/1.070°.
  - Elapsed: 83.25 seconds; maximum child RSS: 285,294,592 bytes.
  - Swap was unchanged; no recorded thermal or performance warning.
- Fixed leave-one-view-out diagnosis:
  - Baseline remained exactly 23/124 accepted.
  - Omit back: 66/124 accepted; omit down: 54/124; omit left: 34/124.
  - Omit up/front/right: 16/13/12 accepted, all worse than baseline.
  - Elapsed: 156.76 seconds; maximum child RSS: 283,754,496 bytes.
  - Swap decreased by 8 MB; no recorded thermal or performance warning.
- Rotation-medoid consensus diagnosis:
  - Synthetic corrupted-view, split-evidence, deterministic tie-break, and
    full ERP/Vision integration gates pass.
  - Accepted 36/124 pairs; 88 failed as insufficient consensus.
  - Selected-view histogram for 1/2/3/4/5 views: 15/25/48/35/1.
  - Median/p95 selected-fit residual: 0.585°/0.885°.
  - Elapsed: 61.65 seconds; maximum child RSS: 283,115,520 bytes.
  - Swap was unchanged; no recorded thermal or performance warning.
- Temporally causal reliability diagnosis:
  - Unit tests prove current observations cannot affect current selection;
    the full synthetic ERP/Vision gate passes.
  - Accepted 86/124 pairs; 23 residual and 15 step failures.
  - First gap is 23 frames/0.92 seconds; later gaps have maximum length three.
  - Selected front/up/right/left/down/back 124/120/119/97/35/3 times.
  - Elapsed: 66.29 seconds; maximum child RSS: 282,148,864 bytes.
  - Swap was unchanged; no recorded thermal or performance warning.
  - v6 reproduced v5 and materialized 124 privacy-safe local steps: 86 valid
    quaternions and 38 explicit null gaps, with no absolute paths.
- Flat homographic post-warp remains rejected as the primary stabilization
  path; see `docs/experiments/vision-homographic-motion-probe.md`.

## Rejected

- Do not present `fixed-last5-stabilized-v1.mp4` or
  `fixed-last5-stabilized-v2.mp4` as successful stabilization candidates.
- Do not widen rectilinear FOV again as the primary shake remedy.
- Do not treat the synthetic ERP source-motion pass as evidence of real-media
  comfort or stabilization quality.
- Do not raise the 1.25° scalar step cap merely to avoid a gap; increase
  temporal sampling or add axis-specific calibration evidence.

## Pending

- Treat hard-radius rotation-medoid selection as a negative baseline.
  Investigate a temporally causal reliability prior, foreground/near-field
  exclusion, or continuous robust view weighting. Do not widen the radius
  after observing v4, select by final acceptance, globally discard a view,
  relax fit thresholds, or render a viewer candidate.
- Implement a temporally causal reliability selector whose current-pair
  subset depends only on earlier-pair disagreement. Validate that a corrupt
  observation cannot affect its own selection, then compare it without
  changing the all-ray baseline or fit bounds.
- Persist causal fitted rotations in a separate privacy-safe analysis
  artifact and define a versioned gap policy. Keep the initial 0.92-second
  gap explicit; do not silently interpolate it or render a viewer candidate.
- Gap classification is complete: nine interior runs totaling fifteen steps
  are bridge candidates; the initial 23-step boundary gap is unbridgeable.
  Implement and angularly validate spherical short-gap reconstruction on
  known synthetic motion before applying it to real steps.
- Local-step SLERP now recovers a known smooth 1°→4° synthetic sequence
  across a two-step gap within 1e-6 radians, while boundary gaps remain null.
  Materialize a candidate real artifact without treating it as measured or
  as an absolute path.
- The real bridge candidate contains 86 measured, 15 interpolated, and 23
  boundary-invalid steps. Transitions touching interpolation have maximum
  local-step change 0.432°; the artifact-wide valid maximum is 1.797°.
  Build a connected relative segment starting only after the initial gap.
- Relative-segment assembly is the active milestone. Every segment must use
  an independent identity anchor and must make no orientation claim across
  remaining invalid gaps.
- The real artifact has one independently anchored segment from 0.92–4.96
  seconds with 102 samples. Raw angular speed median/p95 is 10.80°/24.86° per
  second and scalar jerk-proxy p95 is 9,120°/s³. Next validate quaternion
  smoothing on static, slow-turn, jitter, and quaternion-sign fixtures.
- Quaternion smoothing passes all four fixtures. On the real segment,
  angular-speed p95 falls 24.86→7.19°/s and jerk-proxy p95
  9,119.6→257.3°/s³; maximum correction is 1.40°. Next lock
  `inverse(R) * S` and renderer yaw/pitch/roll conventions synthetically.
- Quaternion composition now has unit tests for no-stabilization identity,
  pure-yaw inverse correction, and composed yaw/pitch/roll round trips.
  Run the existing host v360 convention gate before exporting real commands.
- FFmpeg marker and known-motion render gates pass. The real canonical
  candidate loses to fixed on the translation proxy (median step 3.61 vs
  2.24 px; p95 vector change 11.49 vs 7.75 px). Diagnostic inverse is worse
  than canonical, so simple sign reversal is rejected. Human comfort review
  of fixed versus canonical is now required.
- Owner review judged fixed-forward less dizzy. Canonical action-natural v1
  is rejected. Diagnose residuals by viewport and vertical image band before
  considering foreground masks or spatial weights.
- Spatial diagnostics now retain only normalized grid-band RMS residuals;
  no pixels or coordinates are persisted. Targeted unit tests pass. Run the
  synthetic host gate, then the same bounded real interval into a new v7
  directory.
- v7 reproduced 86/124 causal acceptance. Median residual rises from top to
  bottom in front, left, and down, but not universally in right/up. Define an
  equatorial-only bottom-third exclusion and evaluate it together with the
  unmasked baseline on held-out source time 35–40 seconds.
- Real-media estimator thresholds, gap rate, parallax behavior, source-path
  smoothing, and `action-natural` output remain unverified.

## Next commands

Run from the repository root:

```sh
git status --short
git log -1 --oneline
git status --branch --short
python3 scripts/check_handoff.py
python3 -m unittest discover -s tests -v
```

For the active spatial-residual milestone:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-spatial-v7" \
  --config config/old-ghost-road-multiview-motion-causal-v1.json \
  --source-id old-ghost-road-25-30-spatial-v7 \
  --start 25 --duration 5
```

For the active milestone, the intended next command will be a bounded runner
using the Old Ghost Road ERP at 25–30 seconds and an external artifact output:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps12.5-v1" \
  --config config/old-ghost-road-multiview-motion-v1.json \
  --source-id old-ghost-road-25-30-fps12.5-v1 \
  --start 25 --duration 5
```

The 12.5 fps command above has completed and must not overwrite its output.
The following 25 fps command has also completed and must not overwrite its
output:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-v1" \
  --config config/old-ghost-road-multiview-motion-fps25-v1.json \
  --source-id old-ghost-road-25-30-fps25-v1 \
  --start 25 --duration 5
```

After validating the uncommitted per-view diagnostics, run this new bounded
analysis. It must write a new directory and must not overwrite either prior
result:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-per-view-v2" \
  --config config/old-ghost-road-multiview-motion-fps25-v1.json \
  --source-id old-ghost-road-25-30-fps25-per-view-v2 \
  --start 25 --duration 5
```

The per-view command above has completed and must not be rerun into the same
directory. The exact next implementation check is:

```sh
python3 -m unittest tests.test_so3 tests.test_real_motion_report \
  tests.test_bounded_multiview_motion -v
```

That targeted check passes. After the synthetic host gate, run the bounded
real comparison into a new directory:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-leave-one-out-v3" \
  --config config/old-ghost-road-multiview-motion-fps25-v1.json \
  --source-id old-ghost-road-25-30-fps25-leave-one-out-v3 \
  --start 25 --duration 5
```

The leave-one-out command above has completed and must not be rerun into the
same directory. The exact next command is:

```sh
python3 -m unittest tests.test_view_consensus \
  tests.test_real_motion_report tests.test_bounded_multiview_motion -v
```

The targeted unit tests and synthetic host gate pass. Run the consensus
comparison into a new directory:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-consensus-v4" \
  --config config/old-ghost-road-multiview-motion-consensus-v1.json \
  --source-id old-ghost-road-25-30-fps25-consensus-v4 \
  --start 25 --duration 5
```

The consensus command above has completed and must not be rerun into the same
directory. The exact next command is:

```sh
python3 -m unittest discover -s tests -v
```

The causal selector unit and synthetic integration gates pass. Run its real
comparison into a new directory:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-causal-v5" \
  --config config/old-ghost-road-multiview-motion-causal-v1.json \
  --source-id old-ghost-road-25-30-fps25-causal-v5 \
  --start 25 --duration 5
```

The causal command above has completed and must not be rerun into the same
directory. The exact next command is:

```sh
python3 -m unittest discover -s tests -v
```

The privacy-safe causal rotation-step artifact tests and synthetic host gate
pass. Materialize it into a new real result directory:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-25-30-fps25-causal-steps-v6" \
  --config config/old-ghost-road-multiview-motion-causal-v1.json \
  --source-id old-ghost-road-25-30-fps25-causal-steps-v6 \
  --start 25 --duration 5
```

The v6 command above has completed and must not be rerun into the same
directory. The exact next command remains:

```sh
python3 -m unittest discover -s tests -v
```

## External artifacts

- Artifact root is configured outside Git through `AEGIS_DATA_DIR`.
- Prior Old Ghost Road evidence is under
  `outputs/auto-directed/old-ghost-road-30s-v1/` relative to that root.
- The 12.5 fps source-motion evidence is under
  `outputs/source-motion/old-ghost-road-25-30-fps12.5-v1/`.
- The 25 fps comparison is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-v1/`.
- The per-view 25 fps diagnosis is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-per-view-v2/`.
- The fixed leave-one-view-out diagnosis is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-leave-one-out-v3/`.
- The rotation-medoid consensus diagnosis is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-consensus-v4/`.
- The temporally causal diagnosis is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-causal-v5/`.
- The causal local-rotation artifact is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-causal-steps-v6/`.
- The classify-only gap result is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-causal-gap-policy-v1/`.
- The bridged local-step candidate is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-bridged-steps-v1/`.
- The connected relative segment is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-relative-segment-v1/`.
- The action-natural smoothed segment is under
  `outputs/source-motion/old-ghost-road-25-30-action-natural-smoothing-v1/`.
- The 1920x1080 fixed/canonical review pair is under
  `outputs/stabilization/old-ghost-road-25.92-29.96-action-natural-v1/`.
- The spatial residual diagnosis is under
  `outputs/source-motion/old-ghost-road-25-30-spatial-v7/`.

## Active agents

No delegated work is required to resume this checkpoint. Any agent UI may
show completed historical agents; their results have already been integrated
or recorded above.

## Safety and claims

- Do not commit benchmark media, generated videos, extracted frames, absolute
  local paths, or identity data.
- Do not claim real-media stabilization success until an explicit benchmark
  analysis and render gate passes.
- Treat `action-natural` parameters and comfort thresholds as hypotheses.
