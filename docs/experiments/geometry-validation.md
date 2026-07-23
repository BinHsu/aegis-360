# Geometry validation

Status: Planned

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

## Run record

Hardware/OS, FFmpeg version/build, interpolation, commands, commit, results,
artifacts, limitations and conclusion: TBD. No result has been observed.
