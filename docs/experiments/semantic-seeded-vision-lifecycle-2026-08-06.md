# Semantic-seeded Vision lifecycle — 2026-08-06

Status: Bounded lifecycle and 110-degree render passed agent pre-review

## Question and decision

Can a mutual-unique semantic acquisition automatically provide the exact
viewport and box needed to seed Apple Vision, then survive Core ML detector
refresh without manual box transcription or subject reassignment?

A pass requires a path-free seed manifest, exact viewport geometry, all Vision
frames tracked, visual confirmation of one subject, one compatible same-class
detection per refresh, an active lifecycle throughout and no identity or
editorial-persistence claim. A pass permits planner integration for this
bounded isolated segment. It does not establish cross-viewport handoff.

## Configuration

- Repository baseline before implementation: `2c5cae3`.
- Hardware: fanless Apple Silicon MacBook Air M4, 16 GB unified memory.
- OS: macOS 26.5.2 build 25F84; FFmpeg 8.1.1.
- Source: Old Ghost Road, SHA-256
  `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`.
- Acquisition: `semantic-track:000007`, person, acquired at 68.5 seconds.
- Viewport: right, yaw 90 degrees, pitch 0 degrees, HFOV 100 degrees,
  416x416. Duration 4 seconds at 4 fps.
- Seed selection: smallest maximum normalized box dimension, then viewport ID
  and detector source index. One observation was eligible; source index 3178.
- Initial detector box, top-left coordinates: x 0.15936845, top 0.44103593,
  width 0.20361473, height 0.54433397. The manifest converts it to Apple
  Vision bottom-left y 0.01463010.
- Vision: `VNTrackObjectRequest` revision 1, accurate level.
- Refresh: FLOAT32 YOLOX-Tiny Core ML, confidence 0.25, NMS IoU 0.45,
  one-source-pixel geometry tolerance, 12-degree compatibility.
- Lifecycle: two missing-refresh grace samples, 0.75 confidence decay.

The seed manifest contains no source path, pixels or embeddings. Its source
video path remains an explicit runtime argument. Temporary extracted frames
and the visual contact sheet were kept under the system temporary directory,
not in durable artifacts or Git.

## Results

`scripts/build_semantic_vision_seed.py` reconstructed the acquisition without
manual numeric arguments. `scripts/run_semantic_vision_seed_gate.sh` reproduced
the earlier manual run: the only JSON difference after removing source ID was
the final decimal representation of the initial y value; all subsequent
tracking outputs were identical.

- Vision: 16 requested, 16 tracked, zero lost, zero errors, persistence 1.0.
- Maximum spherical center step: 1.500729 degrees; no seam crossing.
- A five-frame box-overlay contact sheet at 68.5, 69.5, 70.5, 71.5 and 72.25
  seconds was visually inspected. Every box stays on the same person in a blue
  jacket; no background adhesion or subject switch is visible.
- Refresh: all 16 timestamps contain exactly one accepted compatible person;
  no bicycle, rejected target geometry, miss or ambiguity occurs.
- Lifecycle: all 16 events consumed, active throughout, none rejected before
  start or after termination. Every state continues to set
  `identity_verified=false` and `editorial_persistence_allowed=false`.
- Manifest-driven refresh run: 4.947 seconds elapsed, 0.264 seconds model load,
  0.331 seconds Core ML inference and 404,389,888-byte peak RSS. Thermal and
  swap state were not measured; this is not a sustained-performance claim.

External evidence relative to `AEGIS_DATA_DIR`:

- `outputs/semantic-tracklets/old-ghost-road-t60-90-yolox-v2-quality90-mutual12-v2/`
- `outputs/semantic-vision-seeds/old-ghost-road-track000007-4s-v1.json`
- `outputs/vision-tracking-gate/old-ghost-road-t68p5-yaw90-semantic-person-track000007-v2-manifest/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t68p5-yaw90-person-track000007-4s-v2-manifest/`

## Conclusion and follow-up

The isolated-person integration gate passes. A semantic tracklet can now seed
the native tracker reproducibly, with exact viewport aspect, yaw, pitch, FOV
and coordinate-origin conversion. This removes the manual-box dependency.

## Planner and render follow-up

The unchanged `greedy-first-slice-v1.toml` selects the person for all 16
decisions. The static renderer representation holds approximately yaw 60.07
degrees and pitch -28.27 degrees for four seconds, producing a 63.94-degree
maximum effective difference from fixed and passing the existing 8-degree,
two-second pose floor.

The first render exposed an integration bug: lifecycle adaptation used the
110-degree forward/output viewport FOV as though it were the person's angular
extent. Framing safety then added subject padding and rendered 130 degrees.
That version is rejected. The seed manifest now computes the selected box's
actual 19.664-degree spherical horizontal extent, lifecycle candidates carry
that separately from forward FOV, and the corrected render remains at the
110-degree minimum.

Corrected fixed and auto peers are both 1920x1080 H.264 High, yuv420p, 25 fps,
libx264 fast/CRF 18. Mechanical pre-review passes. Paired frames at relative
0.5, 2.0 and 3.5 seconds show the fixed view clipping the blue-jacketed person
at the right edge while auto centers that person and retains nearby people and
environment. No visible blur, blocking, seam break or subject loss was found.

The existing 160x90, 6 fps translation-only shake proxy reports zero median
and p95 translation/vector change for both renders across 23 pairs. This is
only a statement that the proxy detects no additional translational jitter;
it does not assess roll, perspective, comfort or viewer preference.

Corrected external artifacts:

- `outputs/semantic-vision-seeds/old-ghost-road-track000007-4s-v2-extent.json`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v3-extent-corrected/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v4-extent-render/`

The prior `v2-render` directory is rejected because it used 130-degree FOV and
required manual bundle assembly before pre-review. Do not send that version to
the owner.

## Remaining limits

The run is intentionally easy: one visible person and one compatible detector
result at every sample. It does not exercise missing grace, ambiguity during a
live track, leaving the viewport, seam handoff or occlusion. Next convert this
owner-reviewed result into a reusable bundle builder, then select a real
view-exit/ambiguity segment to test fail-closed handoff behavior. Do not infer
persistent identity from this single-view success.
