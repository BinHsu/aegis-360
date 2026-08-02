# Current handoff

Updated: 2026-08-02T18:45:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 52ab8c3
Remote status: `origin/main` contains the baseline commit
Working tree at checkpoint: framing-quality and tracklet milestone pending commit

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The immediate objective is to turn mutual-unique semantic acquisitions
into seeded Vision tracking without inventing identity.

## Last completed milestone

Added the privacy-safe `aegis360.semantic-detector-events.v2` artifact and a
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

The event contract is now v2 because v1 omitted viewport pixel dimensions and
therefore could not reproduce normalized-box ray geometry independently. V2
was rerun in a new external directory; v1 is rejected for spherical conversion.

The established viewport-ray convention converts v2 boxes to spherical
centers/extents. Same-time, same-class spherical dedup reduces 255 observations
to 240 clusters: 15 contain two source views and none exceeds two. All original
provenance remains, while identity and editorial persistence remain false.

A diagnostic geometric association finds a stable real person from 67.75 to
78.75 seconds around yaw 60.7 degrees, pitch -24.3 degrees. A preceding
down-to-right association contains a visible geometry jump, so nearest geometry
is not accepted as identity. No plan or render was produced.

A tunable subject-framing gate now quarantines boxes at or above 0.9 normalized
width/height as unsuitable for isolated subject framing, not as detector false
positives. It quarantines 32/255 observations, including all 19 suspect `up`
boxes. This threshold was derived after inspecting the run and remains a
proposal pending held-out validation.

A detector-only tracklet diagnostic requires mutual-unique compatibility
within 12 degrees, two confirmations over 0.25 seconds and two grace samples.
It acquires 18 fresh IDs, terminates 15 and reports ambiguity in 24/120 samples.
The longest outdoor person segment is about four seconds; the apparent longer
nearest-neighbor chain fragments safely. Seeded tracking is therefore next.

## Repository state

- Expected branch: `main`; baseline `52ab8c3` is present on `origin/main`.
- Benchmark media, model weights, contact sheets and generated artifacts are
  external and gitignored.
- Signing may require an unavailable interactive SSH-key passphrase. Prior
  milestone commits intentionally used `git -c commit.gpgsign=false commit`
  without changing global Git settings.
- Current docs replace superseded state; Git history is the archive.

## Verified

- `python3 -m unittest discover -s tests -v`: 248 tests passed.
- Re-run the handoff validator before committing this milestone.
- Real input produced exactly 120 frames for each of six serial streams.
- Core ML model load count is one; no extracted frame is persisted.
- The external artifact contains only `events.json` and `metrics.json`.
- Source IDs and durable artifacts contain no absolute input path.
- V2 dimensions make viewport projection self-contained; old v1 fails closed.
- Seam and adjacent-view synthetic duplicates merge with provenance retained.
- Ambiguous one-to-many matches do not choose a nearest winner; terminated IDs
  are never reused.

## Rejected

- Do not interpret raw detector count or score as editorial utility.
- Do not claim cross-view duplicates are separate people or a temporal series
  is one identity.
- Do not consume semantic-event v1 for spherical geometry; use v2.
- Do not promote the suspect `up`-view detections to candidates unchanged.
- Do not call quarantined oversized boxes detector false positives; context may
  still use the scene.
- Do not promote the 0.9 framing threshold to an accepted default without
  held-out evidence.
- Do not lower confidence, challenger hold or switch margin from this excerpt.
- Do not render until a sustained non-ego lifecycle survives semantic review.
- Do not return to stabilization-threshold or wider-FOV tuning for this POC.

## Pending

- Seed the existing bounded Vision tracker after mutual-unique semantic
  acquisition on the correct rectilinear frame and box.
- Refresh the track with spherical detector clusters; multiple compatible
  same-class clusters remain ambiguous and cannot reset lifecycle grace.
- Treat viewport exit as a handoff request, not identity proof. Reacquisition
  after termination must use a fresh ID.
- Inspect the tracked candidate before planner integration; render only if it
  is credible and clears unchanged hysteresis.
- Global planning, richer interest signals and verified identity remain later.

## Next commands

Run from the repository root. First validate and deliver this milestone:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_handoff.py
git diff --check
git status --short
```

Then inspect the native tracker and refresh contracts before temporal wiring:

```sh
sed -n '1,220p' src/aegis360/detector_refresh.py
sed -n '1,300p' src/aegis360/refresh_lifecycle.py
sed -n '1,280p' scripts/run_yolox_refresh_sequence.py
sed -n '1,280p' tools/vision_tracking_gate.swift
```

Do not feed generic nearest geometry into lifecycle. Use the mutual-unique
acquisition as the seed boundary, let Vision track within a viewport, and use
semantic refresh only through the existing fail-closed association contract.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. New immutable evidence:

- `outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v2/`
- `outputs/semantic-spherical/old-ghost-road-t60-90-six-view-yolox-v2-dedup-v1/`
- `outputs/semantic-tracklets/old-ghost-road-t60-90-yolox-v2-quality90-mutual12-v1/`

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
