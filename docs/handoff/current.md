# Current handoff

Updated: 2026-08-09T01:25:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: f213efd
Remote status: `origin/main` contains the baseline commit
Working tree at checkpoint: scene-context contract pending commit

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The immediate objective is a conversation/group candidate using person
coverage plus face-based vertical composition, followed by a bounded VLM
context contract.

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
nearest-neighbor chain fragments safely.

Tracklet acquisitions now retain their path-free source observation
provenance. `semantic_vision_seed` deterministically selects a viewport box,
converts detector top-left coordinates to Vision bottom-left coordinates and
retains exact width, height, yaw, pitch and HFOV. The native runner now accepts
nonzero pitch/HFOV, and a wrapper consumes the seed manifest without manual box
transcription.

The manifest-driven `semantic-track:000007` run covers Old Ghost Road
68.5–72.5 seconds in the right 416x416 viewport. Vision tracked 16/16 frames,
zero lost/error, with 1.500729-degree maximum center step. Agent inspection of
five box overlays confirms the same blue-jacketed person throughout. All 16
Core ML refreshes contain exactly one compatible person, so the lifecycle stays
active and consumes every event. Identity and editorial persistence remain
false. No planner or render was produced.

Planner integration now separates the tracked person's 19.664-degree spherical
extent from the 110-degree forward/output viewport. The unchanged greedy config
selects the person for all 16 decisions; the shot stays near yaw 60.07 degrees,
pitch -28.27 degrees and passes the pose gate for all four seconds.

The first render is rejected because the old conflated extent contract added
framing padding to 110 degrees and produced a 130-degree view. The corrected
render uses 110 degrees. Its fixed/auto peers are 1920x1080 H.264 High yuv420p
at 25 fps with the same renderer contract. Mechanical pre-review passes, and
paired-frame inspection at 0.5/2.0/3.5 seconds finds the same blue-jacketed
person centered in auto without obvious blur, blocking, seam failure or subject
loss. Fixed clips that person at the right edge. A translation-only shake proxy
finds zero median/p95 motion for both, but does not prove comfort or roll.

Owner review rejects the directing result: fixed needs to move right/down and
auto needs to move up to frame the visible people whose mouths move. Centering
one whole-body person box is not an acceptable proxy for a speaking subject.
The lifecycle integration remains valid, but editorial success does not. The
source contains stereo audio; its spatial convention and utility for speaker
localization are unverified.

Semantic planning now has an atomic render-bundle bridge. It copies the four
path-free planning artifacts into staging, passes source paths only through a
temporary render request, requires the pose gate, refuses overwrite, cleans up
failure and publishes only after all three videos exist. A fresh real bundle
passes mechanical pre-review and a durable path scan without manual copying.

The bounded four-view face probe succeeds on all 64 requests. It finds exactly
one right-view face at all 16 timestamps near yaw 61.0–61.5 degrees and pitch
-5.4 to -6.4 degrees. The selected whole-body track's pitch was about -28.3
degrees, validating the owner's upward correction. Another visible group
member is not detected as a face, so single-face framing is rejected.

The closed `aegis360.scene-context.v1` contract lets a human or local VLM
classify a bounded event window as conversation, direct address, coordinated
activity, ambient people or uncertain and request group/single/context scope.
It may select only declared candidate IDs. It has no free text, camera geometry
or identity field; local model provenance requires an exact SHA-256.

## Repository state

- Expected branch: `main`; baseline `f213efd` is present on `origin/main`.
- Benchmark media, model weights, contact sheets and generated artifacts are
  external and gitignored.
- Signing may require an unavailable interactive SSH-key passphrase. Prior
  milestone commits intentionally used `git -c commit.gpgsign=false commit`
  without changing global Git settings.
- Current docs replace superseded state; Git history is the archive.

## Verified

- The full repository suite passes: 257 tests. The handoff validator and diff
  checks pass for this milestone.
- Vision frame and sequence shell gates pass with the added face request.
- The full repository suite passes: 261 tests. Scene-context validation,
  handoff and diff checks pass for the contract milestone.
- Real input produced exactly 120 frames for each of six serial streams.
- Core ML model load count is one; no extracted frame is persisted.
- The external artifact contains only `events.json` and `metrics.json`.
- Source IDs and durable artifacts contain no absolute input path.
- V2 dimensions make viewport projection self-contained; old v1 fails closed.
- Seam and adjacent-view synthetic duplicates merge with provenance retained.
- Ambiguous one-to-many matches do not choose a nearest winner; terminated IDs
  are never reused.
- Manifest-driven tracking reproduces the manual trace except source ID and the
  final decimal representation of the initial y coordinate.
- Temporary tracking frames/contact sheet were removed or remain under system
  temporary storage; no pixels entered Git or durable evidence.
- The automated bundle passes equal-encoder and pose gates and retains no
  absolute source path in its durable JSON.
- The face sequence is 16/16 stable for one face, deletes temporary pixels and
  retains no source path, face image, embedding, name or identity claim.

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
- Do not generalize one isolated 16-frame Vision success to crowded identity,
  occlusion, seam or cross-viewport handoff.
- Do not send the `v2-render` output to the owner; its 130-degree FOV came from
  conflating subject extent with output FOV.
- Do not call `v4-extent-render` or `v5-automated-bundle` an editorial pass;
  owner review rejects their speaking-person composition.
- Do not infer active speaker from a person box, mouth motion or uncalibrated
  stereo audio alone.
- Do not center or crop a conversation candidate from the only detected face;
  face recall missed another owner-observed member of the interaction group.
- Do not lower confidence, challenger hold or switch margin from this excerpt.
- Do not render until a sustained non-ego lifecycle survives semantic review.
- Do not return to stabilization-threshold or wider-FOV tuning for this POC.

## Pending

- Build a stable group direction from simultaneous person coverage and use the
  face only as an upward composition anchor.
- Connect a validated group-scope decision to deterministic spherical group
  geometry, with face evidence affecting vertical composition only.
- Establish whether audio is merely stereo playback or has a usable, verified
  direction convention before adding audio localization.
- Later select a real view-exit/ambiguity segment. Treat exit as a handoff
  request, not identity proof; post-termination acquisition uses a fresh ID.
- Global planning, richer interest signals and verified identity remain later.

## Next commands

Run from the repository root. First validate and deliver this milestone:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After validation, inspect the existing Apple Vision runner patterns before a
bounded face-evidence probe:

```sh
rg -n 'VNDetectFace|VNDetectHuman|Vision' scripts native src tests
sed -n '1,180p' docs/design/interest-model.md
```

Keep face evidence path-free and temporary-pixel-only. Preserve
`GEOMETRIC_ONLY`; a face or moving mouth is not identity or proven speech.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. New immutable evidence:

- `outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v2/`
- `outputs/semantic-spherical/old-ghost-road-t60-90-six-view-yolox-v2-dedup-v1/`
- `outputs/semantic-tracklets/old-ghost-road-t60-90-yolox-v2-quality90-mutual12-v2/`
- `outputs/semantic-vision-seeds/old-ghost-road-track000007-4s-v1.json`
- `outputs/vision-tracking-gate/old-ghost-road-t68p5-yaw90-semantic-person-track000007-v2-manifest/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t68p5-yaw90-person-track000007-4s-v2-manifest/`
- `outputs/semantic-vision-seeds/old-ghost-road-track000007-4s-v2-extent.json`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v3-extent-corrected/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v4-extent-render/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v5-automated-bundle/`
- `outputs/vision-face-sequence/old-ghost-road-t68p5-4s-4fps-four-view-v1/evidence.json`

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
