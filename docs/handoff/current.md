# Current handoff

Updated: 2026-08-02T18:00:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: fb4d6e8
Remote status: `origin/main` contains the baseline commit
Working tree at checkpoint: only this checkpoint metadata differs from baseline

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The immediate objective is to turn continuous multi-view detector
events into conservative spherical candidate lifecycles without inventing
identity.

## Last completed milestone

Added the privacy-safe `aegis360.semantic-detector-events.v1` artifact and a
load-once Core ML runner for configured serial rectilinear views. Synthetic
tests fix deterministic ordering, bounded geometry, person/bicycle-only
content, path-free provenance, privacy declarations and a six-view 416x416
configuration. The runner refuses overwrite and persists no pixels.

The bounded Old Ghost Road 60–90 second run sampled six views at 4 fps. It
produced all 720 expected timestamp/view rows in 12.614 seconds with
365,527,040-byte peak RSS, 238 person boxes, 17 bicycle boxes and 25 rejected
out-of-frame boxes. Agent inspection confirmed real people outside and inside
the hut across multiple headings. Coverage is materially broader than the
earlier isolated bicycle lifecycle.

The result is pre-identity. Cross-view duplicates remain, and all 19 `up`-view
person boxes are unusually large (mean normalized area about 0.739), so pole or
projection-boundary artifacts must be handled before candidate acquisition.
No plan or render was produced from these raw counts.

## Repository state

- Expected branch: `main`; baseline `fb4d6e8` is present on `origin/main`.
- Benchmark media, model weights, contact sheets and generated artifacts are
  external and gitignored.
- Signing may require an unavailable interactive SSH-key passphrase. Prior
  milestone commits intentionally used `git -c commit.gpgsign=false commit`
  without changing global Git settings.
- Current docs replace superseded state; Git history is the archive.

## Verified

- `python3 -m unittest discover -s tests -v`: 238 tests passed.
- `python3 scripts/check_handoff.py`: passed.
- Real input produced exactly 120 frames for each of six serial streams.
- Core ML model load count is one; no extracted frame is persisted.
- The external artifact contains only `events.json` and `metrics.json`.
- Source IDs and durable artifacts contain no absolute input path.

## Rejected

- Do not interpret raw detector count or score as editorial utility.
- Do not claim cross-view duplicates are separate people or a temporal series
  is one identity.
- Do not promote the suspect `up`-view detections to candidates unchanged.
- Do not lower confidence, challenger hold or switch margin from this excerpt.
- Do not render until a sustained non-ego lifecycle survives semantic review.
- Do not return to stabilization-threshold or wider-FOV tuning for this POC.

## Pending

- Convert event box centers/extents to spherical geometry using viewport pose
  and FOV, with synthetic seam/pole tests.
- Merge same-timestamp, same-class cross-view duplicates through the existing
  spherical-dedup boundary while preserving every observation's provenance.
- Define a fail-closed pole/boundary policy from geometry, not from one
  clip-specific score threshold.
- Feed merged observations into conservative fresh-candidate acquisition and
  lifecycle logic with unique new IDs after termination.
- Inspect sustained candidates before planner integration; render only if one
  is visibly credible and clears unchanged hysteresis.
- Global planning, richer interest signals and verified identity remain later.

## Next commands

Run from the repository root. First validate and deliver this milestone:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_handoff.py
git diff --check
git status --short
```

Then inspect the existing spherical merge and viewport geometry contracts:

```sh
sed -n '1,300p' src/aegis360/spherical_dedup.py
sed -n '1,260p' src/aegis360/new_track_acquisition.py
sed -n '1,260p' src/aegis360/viewport_geometry.py
```

If `viewport_geometry.py` does not exist, locate the established pixel/ray
conversion with `rg -n "pixel.*yaw|viewport.*ray|spherical" src tests` before
adding another geometry implementation.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. New immutable evidence:

- `outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v1/`

Relevant prior evidence:

- `outputs/yolox-refresh-sequence/old-ghost-road-t60-yaw0-bicycle-8s-4fps-v3/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t105-yawm90-person-8s-4fps-v4/`
- `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v4-render-ready/`

Do not overwrite or commit these directories.

## Active agents

No delegated work is active or required to resume this checkpoint.

## Safety and claims

- Do not commit media, generated video, extracted frames, model weights,
  faces, audio, absolute paths or identity data.
- Analysis and rendering remain offline; setup/acquisition requires explicit
  network action.
- Preserve bounded queues and the 16 GB unified-memory constraint.
- Treat semantic/geometry continuity as nonidentity unless a stronger adapter
  proves otherwise.
- Do not claim directing quality, real-time output, thermal stability or
  identity continuity beyond the recorded experiment.
