# Geometry validation

Status: In progress — pure geometry slice passed; renderer comparison pending

## Question

Do internal spherical conventions and the renderer mapping remain correct at
ordinary locations, the ERP seam and poles?

## Decision unlocked

Freeze coordinate conventions and tolerances; permit benchmark perception and
render work to proceed.

## Inputs

Generated ERP grids, cardinal labels, seam-straddling shapes, pole markers and
known timestamped camera paths. No downloaded media is required.

## Procedure

1. Generate fixtures deterministically and record dimensions/hash.
2. Test pixel/direction round trips, distance, circular mean and yaw unwrap.
3. Render known yaw/pitch/FOV poses with installed FFmpeg `v360`.
4. Compare expected marker locations and seam-crossing paths.
5. Exercise pole-adjacent and randomized finite inputs.

## Metrics and acceptance criteria

Record pixel/angular round-trip error, marker-center error, discontinuities,
NaN/Inf count and path derivative outliers. Proposed gate: all cardinal/seam
fixtures select the intended hemisphere, no NaN/Inf, no long-way seam rotation,
and errors within tolerances documented from fixture resolution before the run.

## Run record: pure geometry slice, 2026-07-23

- Hardware: MacBook Air (Apple M4, 10 cores, 16 GB unified memory)
- OS: macOS 26.5.2 (build 25F84), arm64
- Python: CPython 3.14.4
- Starting commit: `81453cb` (the evidence-slice changes were uncommitted)
- Dependencies: Python standard library only
- Command: `python3 -m unittest discover -s tests -v`
- Result: 12 tests passed in 0.001 seconds
- Deterministic sample: 1,000 integer pixel centers at 1920x960, seed 360
- Maximum observed pixel round-trip error: `2.2737367544323206e-13`
  pixels
- Maximum observed angular round-trip error: `0` radians for that sample
- Seam path: wrapped yaw sequence 170, 175, 179, -179, -175, -170
  degrees unwrapped with a maximum step of approximately 5 degrees, with no
  long-way rotation
- Pole checks: exact-pole yaw invariance and finite, symmetric distances for
  pole-adjacent points passed

The implementation and regression tests are in `src/aegis360/geometry.py` and
`tests/test_geometry.py`. This run validates the internal pixel-center mapping,
yaw wrap/unwrap, direction mapping and great-circle distance. It does **not**
complete this experiment or freeze renderer conventions: generated image
fixtures, FOV/orientation, interpolation and comparison with FFmpeg `v360`
8.1.1 remain untested. No performance conclusion is drawn from unit-test
runtime.
