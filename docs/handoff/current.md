# Current handoff

Updated: 2026-08-11T05:15:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 753e2c5
Remote status: rejected-model evidence commit and checkpoint are ready to push
Working tree at checkpoint: only this checkpoint metadata differs from baseline

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The conversation-group composition gate is accepted; the immediate
objective is a checksummed offline context adapter selecting fixed proposals.

## Last completed milestone

The privacy-safe semantic-event v2 pipeline, load-once Core ML runner,
spherical dedup and detector-only tracklet diagnostics remain the perception
foundation. V1 is rejected because it lacked viewport dimensions. The real
30-second run is recorded in the experiment docs; all continuity remains
geometric/nonidentity, and the tunable oversized-box quarantine remains
unvalidated on held-out footage.

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

The closed `aegis360.scene-context.v2` contract makes geometry declare person,
group and context proposals before human/local-VLM review. A group references
2+ declared person proposals but asserts no identity; review selects exactly
one proposal matching its requested scope. It has no free text, camera geometry
or identity field, and local model provenance requires an exact SHA-256. V1 is
rejected because it made review compose fragmented cross-time person IDs.

Two-person spherical groups exist at 8/16 samples. They are stable near yaw
53.9–54.4 degrees; the body-based pitch near -25 degrees becomes -5.4 to -6.4
degrees after a bounded compatible-face correction. Membership, yaw and FOV
are unchanged. The other eight samples miss the second person, so per-frame
group presence is not render-ready and needs window-level bounded persistence.

The new window aggregator requires explicit group context and accepts the real
8/16 observation ratio at an inclusive 0.5 floor. It yields yaw 54.083 degrees,
pitch -6.124 degrees and 51.474 degrees required horizontal coverage. It stores
no cross-time member IDs and labels the association geometric/nonidentity.

Window geometry now declares proposal-local `person-slot` members from the
minimum simultaneously observed group size and one group proposal referencing
them. Slots are coverage provenance, not identities. With that selected group,
the unchanged primary greedy config chooses it 16/16 over forward context.

Geometry generation no longer consumes scene context. The new atomic,
refuse-overwrite `aegis360.window-group-proposal.v1` artifact is created first;
a separate human/local-VLM adapter selects one proposal through scene-context
v2; a planner adapter verifies that context reproduces the proposal candidates
before producing the existing semantic planning/render contract.

The first real artifact used the only detected face as the group pitch
(-6.124 degrees). Although its 1080p render passed mechanical checks, agent
contact-sheet review rejected it because the group was pulled too high and a
second visible member was crowded against the lower edge. It was not sent to
the owner. The replacement limits face correction to a tunable 5 degrees and
renders yaw 54.083, pitch -20.278 and HFOV 110 degrees. It selects the group
16/16, reaches 56.615 degrees fixed/auto pose difference, passes the mechanical
gate, and retains all three visible heads without obvious codec or seam damage.
The nearby cap-wearing person remains partially cropped below the torso.
On 2026-08-11 the owner accepted the auto render as successfully capturing the
two people in conversation. This accepts group framing only; it does not prove
speaker identity, active-speaker inference, automatic context classification,
subject switching or longer-window tracking.

The generic local-model importer accepts only the four closed decision fields,
verifies the exact model asset SHA-256, binds the result to proposal-owned
candidates, validates scene-context v2, writes atomically and refuses overwrite.
It permits uncertain/no-selection and rejects free text, geometry and invented
candidate IDs. SmolVLM2 500M Video MLX BF16 was acquired and ran without swap,
but three prompt-only and two grammar-constrained runs failed semantic or
cross-field validation. It is rejected for planner integration; stop tuning.

## Repository state

- Expected branch: `main`; content baseline is `753e2c5`.
- Benchmark media, model weights, contact sheets and generated artifacts are
  external and gitignored.
- Signing may require an unavailable interactive SSH-key passphrase. Prior
  milestone commits intentionally used `git -c commit.gpgsign=false commit`
  without changing global Git settings.
- Current docs replace superseded state; Git history is the archive.

## Verified

- Vision frame and sequence shell gates pass with the added face request.
- The full repository suite passes: 278 tests, including proposal/selection/
  planner contracts.
- Targeted local-context adapter tests pass for checksum provenance, group and
  uncertain decisions, and fail-closed extra geometry/text/candidate IDs.
- The acquired 500M model runs without swap. Grammar fixes syntax but still
  selects wrong semantics or an invalid scope/candidate pair.
- Targeted group geometry tests prove compatible faces change only pitch,
  unrelated faces are ignored and correction magnitude is bounded.
- Window-group tests cover the 0.5 floor, insufficient evidence, non-group
  rejection, nonidentity output and seam-safe aggregation.
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
- Do not call `v4-extent-render` or `v5-automated-bundle` an editorial pass;
  owner review rejects their speaking-person composition.
- Do not infer active speaker from a person box, mouth motion or uncalibrated
  stereo audio alone.
- Do not center or crop a conversation candidate from the only detected face;
  face recall missed another owner-observed member of the interaction group.
- Do not render raw per-frame group availability; it flickers on half the
  samples in this excerpt.
- Do not use the only detected face as the group camera center; the rejected
  pitch -6.124 render visibly miscomposes another group member.
- Do not promote the 5-degree face correction to a universal default; it is a
  tunable POC guard pending held-out evidence.
- Do not consume scene-context v1 or ask review/VLM to compose person IDs;
  geometry owns group proposals and membership provenance.
- Do not lower confidence, challenger hold or switch margin from this excerpt.
- Do not render until a sustained non-ego lifecycle survives semantic review.
- Do not return to stabilization-threshold or wider-FOV tuning for this POC.

## Pending

- Research a larger model; constrained decoding is already verified and is
  insufficient here. Additional weights require explicit acquisition.
- Retain the accepted 5-degree POC guard while adding group/upper-body vertical
  extents and testing held-out footage; do not promote it to a product default.
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

After validation, inspect candidate models without downloading them:

```sh
sed -n '1,240p' model-manifests/candidates.toml
sed -n '1,260p' scripts/import_local_vlm_scene_context.py
```

Keep face evidence path-free and temporary-pixel-only. Preserve
`GEOMETRIC_ONLY`; a face or moving mouth is not identity or proven speech.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. New immutable evidence:

- `outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v2/`
- `outputs/semantic-spherical/old-ghost-road-t60-90-six-view-yolox-v2-dedup-v1/`
- `outputs/semantic-tracklets/old-ghost-road-t60-90-yolox-v2-quality90-mutual12-v2/`
- `outputs/vision-tracking-gate/old-ghost-road-t68p5-yaw90-semantic-person-track000007-v2-manifest/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t68p5-yaw90-person-track000007-4s-v2-manifest/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v3-extent-corrected/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v4-extent-render/`
- `outputs/semantic-planning/old-ghost-road-t68p5-person-track000007-4s-v5-automated-bundle/`
- `outputs/vision-face-sequence/old-ghost-road-t68p5-4s-4fps-four-view-v1/evidence.json`
- `outputs/window-group-proposals/old-ghost-road-t68p5-4s-v2-pitch-guard5/`
- `outputs/semantic-planning/old-ghost-road-t68p5-conversation-group-4s-v3-pitch-guard5-plan/`
- `outputs/semantic-planning/old-ghost-road-t68p5-conversation-group-4s-v4-pitch-guard5-render/`

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
