# Current handoff

Updated: 2026-07-26T11:43:01+08:00
Repository: aegis-360
Branch: main
Baseline commit: 331664d
Remote status: main is two commits ahead of origin/main at this checkpoint
Working tree at checkpoint: 25 fps config, resource capture and result records are uncommitted

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

## Repository state

- Expected branch: `main`.
- Baseline commit: `4b76cb6`.
- Commit `b98b64d` contains the handoff contract, validator, tests and CI
  enforcement. It and the bounded ERP runner were pushed to `origin/main`
  before this checkpoint metadata update.
- Commit `f3c081d` contains the real ERP analysis runner and is not yet pushed
  at this checkpoint.
- Media and generated video remain outside Git under the configured artifact
  root.

## Verified

- `python3 -m unittest discover -s tests -v`
  - PASS: 122 tests including the handoff-contract tests.
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

- Record and commit the 25 fps negative comparison.
- Add privacy-safe per-view fit diagnostics and fused-rotation disagreement,
  then rerun the same 25 fps interval. Do not increase sampling or relax
  thresholds, and do not render a viewer candidate.
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

## External artifacts

- Artifact root is configured outside Git through `AEGIS_DATA_DIR`.
- Prior Old Ghost Road evidence is under
  `outputs/auto-directed/old-ghost-road-30s-v1/` relative to that root.
- The 12.5 fps source-motion evidence is under
  `outputs/source-motion/old-ghost-road-25-30-fps12.5-v1/`.
- The 25 fps comparison is under
  `outputs/source-motion/old-ghost-road-25-30-fps25-v1/`.

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
