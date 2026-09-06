# Structural chapter labeled contrast v1

Status: frozen after independent audit; no feature acquisition

Frozen config SHA-256:
`8baf66a00a008625cd91292aaa8ac0a8794d9fb20338e0acfab054b3a2f7f7a2`.

## Scope and evidence

This asks whether a color-independent spatial descriptor scores one established
activity/context chapter cut above one hard cut that continues the same chapter.
It follows Skiing's palette-dominated failure but never tunes that policy.

Old Ghost Road is a different exact source (SHA-256
`4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`).
The source and labels were previously reviewed, so this is a precommitted
label-selected contrast, not source-level held-out evidence or owner ground
truth. Only the new descriptor values remain unseen.

The primary non-overlapping contrast is event 0005 at 53 seconds
(`within_chapter_cut`, `action_continuation`) versus event 0008 at 84.6 seconds
(`chapter_boundary`, `activity_transition`). Events 0018 at 163.5 and 0019 at
168.4 seconds form a correlated secondary pair because their outer windows
overlap the same intermediate state. That pair has report-only authority.
The config binds each rational time to exact event packet, label-config and
semantic-evidence hashes; a filename or duplicated expected class is not enough.

## Exact direct-source sampling

The source is hashed before and after one direct decode. FFmpeg applies the
global `fps=2:start_time=0:round=near`, then area-scales to 160x80 and emits
gray8. The analysis grid is exactly `n/2` seconds from zero. Each rational
nominal sample chooses the nearest grid point, with earlier-point ties, maximum
error 1/4 second, uniqueness and correct side required. Offsets are ±3.75,
±3.25, ±2.75 and ±2.25 seconds, yielding exactly four samples on each side.
Missing, duplicate or out-of-window samples fail without an artifact.

## Closed descriptor and score

Each frame uses the declared Sobel kernels on gray8, horizontal-wrap and
vertical-reflect borders. Magnitude is `(abs(gx)+abs(gy))/2040`. An 8x4 tile
grid stores mean magnitude and eight unsigned `[0,π)` magnitude-weighted
orientation bins; bins sum to one, or all remain zero for a zero-gradient tile.
Boundary angles use lower-inclusive bins. RGB is forbidden.

Frame descriptors are componentwise arithmetic-meaned into native-coordinate
before/after centers. Window dispersion is the arithmetic mean frame-to-own-
center distance with no alignment. State comparison tries exactly eight whole-
tile horizontal shifts of the after center, using one shared shift for both
components and the smallest shift on ties. This is discrete 45-degree tile
shift tolerance, not general yaw invariance.

Both component distances are tile-mean L1 values normalized to [0,1] and have
weight one half: `Dmag=sum32(|m-n|)/32`,
`Dori=sum32(sum8(|p-q|)/2)/32`, and `D=(Dmag+Dori)/2`. The selected shift is
the `argmin` of this combined D; components cannot align separately. Dispersion
is the arithmetic mean of combined D from exactly four native-coordinate
frames to their own center, with no alignment. Score is
`max(0, state_distance - before_dispersion -
after_dispersion)`. Only final recorded scalars are half-even rounded to eight
decimals; nonfinite or invalid normalization fails.

Vertical reflection is OpenCV-style reflect-101 (`y=-1→1`, `y=H→H-2`).
Orientation is exactly `atan2(gy,gx) mod π` into `[0,π)` before binning.

## Gates

The primary ordinal gate passes only if rounded score(0008) is strictly greater
than rounded score(0005). It makes no effect-size or accuracy claim. All four
scores, components, dispersions, selected shifts and exact sampled grid times
must be reported. Secondary ordering cannot change the gate.

The separately committed synthetic episode schema uses exact rational scalar
states and absolute-difference distance, pinned at SHA-256
`3cd1cc5360c61035adac8c15c7cfda103d0ced31c34cc712d702ff271eee4913`.
It covers true A→B→A, persistent A→B, A→B→C, noisy outer A, returns beyond 60 seconds, equality,
zero transitions and competing exits. Define `entry=D(A0,B0)`,
`exit=D(B1,A1)`, `rA=D(A0,A1)/min(entry,exit)` and
`rB=D(B0,B1)/min(entry,exit)`. Both transitions must be positive; separation is
at most 60 seconds; `rA` and `rB` must each be at most one half. Equality passes
and zero transitions are not pairable. Process entries chronologically, choose
the eligible exit with smallest `rA+rB` then earliest time, and make pairs
disjoint. Persistent changes remain unpaired and must never collapse.

Any real-ranking or synthetic failure rejects the hypothesis. A pass permits
only a separately designed blind replication, never a story boundary, camera
choice or render. Config and fixture hashes must be committed before decoding.

An independent no-artifact audit passed the corrected timing, evidence lineage,
descriptor math, correlated-pair limitation and fixture pairing semantics.
