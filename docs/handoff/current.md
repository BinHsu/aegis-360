# Current handoff

Updated: 2026-07-29T12:00:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 5b0ccfd
Remote status: push the pre-review gate checkpoint described below
Working tree at checkpoint: v8 rejected; renderer-aware pre-review gate active

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
- Baseline commit: `7c8b74a`.
- Commit `b98b64d` contains the handoff contract, validator, tests and CI
  enforcement. It and the bounded ERP runner were pushed to `origin/main`
  before this checkpoint metadata update.
- Commits through `daefbdf` are signed and pushed to `origin/main`.
- Commit `daca112` is intentionally unsigned because the host SSH signing key
  required an unavailable interactive passphrase during this run.
- Media and generated video remain outside Git under the configured artifact
  root.

## Verified

- `python3 -m unittest discover -s tests -v`
  - PASS: 153 tests including privacy-safe spatial-mask aggregation.
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
- The held-out mask comparison accepted 119/124 versus 121/124 for unmasked
  causal fitting. Although median residual fell 0.00790→0.00754 rad, the mask
  lost two accepted pairs and added a step-bound failure. Reject it as the
  default and retain the unmasked causal estimator.
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

The held-out spatial-mask command below has completed. Do not overwrite its
output; choose a new source ID and directory for any repetition:

```sh
python3 scripts/run_real_erp_multiview_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-35-40-equatorial-mask-heldout-v1" \
  --config config/old-ghost-road-multiview-motion-equatorial-mask-v1.json \
  --source-id old-ghost-road-35-40-equatorial-mask-heldout-v1 \
  --start 35 --duration 5
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

The next estimator investigation must obtain spatially independent motion
evidence, for example bounded tile-level registrations. The current
whole-viewport homography only supplies one motion model per viewport, so
masking samples of that model cannot reliably identify a moving foreground.
Validate any tiling approach on synthetic foreground/background motion before
another real-media run.

The active bounded step is a dependency-free tile-rotation consensus with
minimum spatial coverage. Its exact first check is:

```sh
python3 -m unittest tests.test_tile_motion_consensus -v
```

It must reject a coherent local foreground cluster and fail closed when the
apparent background motion lacks configured image-area coverage. Do not wire
native Vision tiling or run benchmark media until this synthetic contract
passes.

That contract now passes four tests: distributed background versus local
foreground, local-cluster coverage failure, split-motion failure, and
deterministic validation. The next bounded step is a generated-image host gate
showing that independently cropped tiles can return divergent Vision
registrations. It must not read benchmark media.

The host gate passes only at the retained 640x360 tile size: configured
2/8/14/20 pixel translations produced 2.10/7.97/11.98/18.59 pixel Vision
proxies. The 320x180 attempt was non-monotonic and is rejected. Tile-local
homographies also pass parent-viewport ray tests at nonzero crop origins.

The next bounded milestone is performance-only: measure a generated 2x2,
1280x720 parent sequence with four 640x360 registrations using a bounded frame
count. Record elapsed time and peak RSS before any six-viewport integration or
benchmark-media run.

A two-frame bootstrap measurement took 3.91 seconds, maximum RSS was
190,332,928 bytes, and `/usr/bin/time` reported zero swaps. It compiled Swift
four times and includes fixture generation/cropping, so do not treat it as
per-frame throughput. The exact next implementation is a compile-once,
multi-frame generated benchmark; no real-media command is authorized by this
checkpoint.

The compile-once runner now measures 96/96 pairs in 0.991 seconds at 25
frames/tile and 496/496 in 2.295 seconds at 125 frames/tile. The longer run is
216.2 registrations/s with 56,852,480 bytes maximum child RSS, unchanged swap,
and no recorded warning. This permits a bounded analysis-only integration;
it does not establish realtime or 30-second sustained performance.

Next implement a versioned tile-evidence artifact and assembly adapter using
the tested parent-viewport crop geometry. Keep four tile sequences serial,
compile Vision once, and preserve the existing whole-viewport causal result
as an unchanged comparison. Do not render or overwrite prior artifacts.

The in-memory assembly adapter is now implemented and passes synthetic tests:
four identity tiles retain all four spatial cells; an independently translated
lower-right tile is rejected while the other three cells remain selected.
Duplicate IDs and invalid crop extents fail closed.

The exact next milestone is the native JSON boundary. Extend or wrap
`tools/vision_motion_probe.swift` so one compile emits a versioned,
privacy-safe artifact for four serial tile sequences. Add a fake/artifact
contract test before connecting it to ERP projection. Do not persist image
paths, pixels, or crop files in the output.

The wrapper boundary is implemented as
`scripts/assemble_vision_tile_evidence.py`. Its artifact contract removes
private manifest/evidence paths, aligns timestamps, validates tile extents,
and sanitizes backend errors. Three artifact tests pass. The next integration
step is to make the bounded real runner optionally generate a 1280x720 parent
viewport, execute four serial 640x360 sequences, and feed this artifact into a
separate tile diagnostic without changing the current causal baseline.

That integration is now active. It must first pass a generated ERP/Vision
smoke gate, keep one viewport's temporary parent/tile frames live at a time,
and emit only aggregate tile selection/failure evidence. No benchmark run or
viewer render occurs before that gate passes.

The generated full-path smoke gate passes 3/3 front-viewport pairs with all
four tiles selected, zero rotation/residual, path-free output, 2.32 seconds
elapsed, and 189,923,328 bytes maximum child RSS.

The next authorized analysis-only command uses a new Old Ghost Road interval
and output:

```sh
python3 scripts/run_real_erp_tile_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-40-45-tile-motion-v1" \
  --config config/old-ghost-road-tile-motion-diagnostic-v1.json \
  --source-id old-ghost-road-40-45-tile-motion-v1 \
  --start 40 --duration 5
```

That command completed and must not overwrite its output. Front/left/up
accepted 103/116/113 of 124 pairs; back/right/down accepted 50/47/49. The run
took 54.37 seconds with 355,368,960 bytes maximum child RSS. Per-viewport
three-of-four tile consensus is rejected as the final fusion boundary.

Next retain the 0.5° tile radius and add a synthetic global selector over all
24 tiles. It must require at least thirteen agreeing tiles and coverage from
at least four viewports. Do not rerun real media until that fail-closed
contract passes.

The synthetic selector and six-viewport ERP/Vision smoke gate now pass. The
smoke gate measured 3/3 global pairs with all 24 tiles and all six viewports.
Run the same development interval only to compare fusion boundaries:

```sh
python3 scripts/run_real_erp_tile_motion.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/outputs/source-motion/old-ghost-road-40-45-global-tile-v2" \
  --config config/old-ghost-road-tile-motion-diagnostic-v1.json \
  --source-id old-ghost-road-40-45-global-tile-v2 \
  --start 40 --duration 5
```

Do not call this a held-out result and do not overwrite v1.

The v2 development comparison completed: global tiles accepted 93/124, with
31 strict-majority failures and no later fit-bound failures. Median selection
was fifteen tiles across five viewports; median residual was 0.00355 rad.

The held-out 45–50 second rule is fixed before running: global accepted pairs
must be at least the unchanged causal baseline count. Run causal first into
`old-ghost-road-45-50-causal-heldout-v1`, then global tiles into
`old-ghost-road-45-50-global-tile-heldout-v1`. Do not change thresholds or
render from either result.

Both held-out commands completed at 124/124, so global passes the coverage
rule. Causal/global median residuals are 0.000776/0.001644 rad and median
steps are 0.002005/0.001675 rad. This is not an accuracy or comfort win.

Next run unchanged causal on the already-used 40–45 second development
interval into `old-ghost-road-40-45-causal-comparison-v1`; compare it with
global v2's 93/124. Do not describe this as held-out evidence.

That comparison completed: unchanged causal accepted 123/124 with one
step-bound failure, versus global's 93/124 and 31 strict-majority failures.
Reject global tiles as the primary fusion boundary and retain them only as a
spatial diagnostic. Do not tune their thresholds.

Next inspect the gap-free 45–50 second causal rotation artifact and reuse the
already-tested relative-path, quaternion smoothing, renderer convention, and
fixed comparison gates. Do not render until path coverage and command
provenance are explicit.

That gate completed. The path has 125 samples over 4.96 seconds with no gap;
maximum smoothing correction is 0.47°. Both fixed and canonical MP4s are
1920x1080 H.264/AAC and exactly 4.96 seconds. Fixed wins the translation proxy:
canonical/fixed p95 step is 2.0/1.0 px and p95 vector change is 2.65/1.0 px.
Both trailing windows are zero.

Do not ask the owner to review this negative candidate. Preserve raw/fixed as
the POC comfort treatment and return to the auto-director path. The next
bounded task is to inspect `docs/experiments/first-auto-directed-slice.md` and
the existing 30-second tracking/planning evidence, then define the smallest
new directing gate without revisiting rejected stabilization thresholds.

That planning-only replay is complete. Generic saliency has zero nonzero
persistence terms, but selections remain `track:000002` 46/60,
`track:000010` 8/60, and context 6/60. The bundle is planned-only under
`outputs/auto-directed/old-ghost-road-30s-v1/`
`bundle-v5-current-persistence-plan/`; do not render it.

Next implement a seam-aware group/context candidate from simultaneous saliency
regions with a bounded wide FOV. Synthetic tests must cover seam crossing,
single-candidate fallback, pole-safe pitch, deterministic membership, and
minimum framing padding before wiring it into the planner.

That geometry is implemented. An all-saliency group was correctly unavailable
because required HFOV was 290–442°. Local clustering produced valid groups on
23/60 frames, but v7 selected them 0/60 under unchanged scoring/hysteresis.
Do not lower the 0.1 switch margin.

Next add a named group-coverage interest signal whose raw value is the number
of distinct covered saliency members and whose normalized value is bounded.
Prove detector confidence is absent, context fallback remains below observed
evidence, and signal ablation is deterministic before adding a new config
weight or replaying the plan.

That gate is complete. `group_coverage` is optional so the original config
remains valid; only `group_context` receives its bounded `count / 3` value.
The new `config/greedy-group-context-v1.toml` keeps the two-second dwell and
0.1 switch margin. Its v8 replay selects context 6/60, group 7/60, and
`track:000002` 47/60, with group context held from 3.0 through 6.5 seconds.

The mechanically checked render is external at
`outputs/auto-directed/old-ghost-road-30s-v1/`
`bundle-v8-group-coverage-render/`. `fixed-forward.mp4`,
`auto-directed.mp4`, and `debug-overlay.mp4` are 1920x1080 H.264/AAC and
approximately 30 seconds. `shake-proxy.json` shows identical auto/debug
motion and comparable fixed/auto final-segment movement. Do not claim comfort
or stabilization success from that proxy.

Next ask the owner to compare the three outputs, concentrating on whether the
3.0–6.5 second group view provides useful context, whether both switches feel
natural, and whether the post-6.5 selection is interesting to an ordinary
viewer. The ending shake is shared source behavior and should be judged
separately from framing. Do not change scoring thresholds before that review.

The owner completed that review and rejected v8: fixed and auto appeared
nearly identical, while fixed appeared clearer. A renderer-aware replay shows
the actual static shots differ from forward by only 0°, 1.68°, and 2.65°,
despite larger planner-keyframe extrema. The old bundle also compared fixed
CRF 23 against auto CRF 0, so its image-quality judgment is confounded.

The render contract now uses libx264 fast/CRF 18/yuv420p for both fixed and
auto. `scripts/check_render_pre_review.py BUNDLE` evaluates decoded stream
comparability and the actual static-shot poses; the v8 bundle correctly exits
1 with zero seconds above its 8° floor. Before any future owner review, run
that gate and visually inspect representative paired frames/contact sheets.
Do not send paths when either check can already reject the candidate.

Next investigate semantic subject candidates and identity continuity before
another 30-second render. A new plan must produce materially differentiated
actual renderer shots without manufacturing switches by lowering hysteresis.

The dependency/model inventory is empty: no local detector weights were found
under the configured data root, and torch, Ultralytics, Core ML Tools, ONNX
Runtime and OpenCV are not installed. Existing Vision tracking requires an
external initial box and cannot hand off across viewports.

The proposed bounded bootstrap is Apple-hosted YOLOv3 Tiny Core ML detection
at low cadence plus `VNTrackObjectRequest` between refreshes. It requires an
explicit model acquisition action; before use, store it outside Git and
record URL, access date, checksum, bytes, labels, model metadata and license.
Do not install Ultralytics as the default: its official distribution is
AGPL-3.0/commercial dual licensed. YOLOX is the Apache-2.0 comparison, not the
first time-to-evidence path.

After model acquisition, the exact next implementation milestone is a Swift
detector probe over generated rectilinear input that emits privacy-safe
`VNRecognizedObjectObservation` labels/boxes and fails closed on missing or
unexpected model outputs. Do not run a real-media tracking or render gate
before that synthetic/model-contract gate passes.

The owner authorized acquisition and the Apple-hosted
`YOLOv3TinyFP16.mlmodel` is now present under the external data root at
`models/apple/yolov3-tiny-fp16/YOLOv3TinyFP16.mlmodel`. The canonical
non-secret record is `model-manifests/manifest.toml`; its SHA-256 is
`73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda`
and its byte size is 17,769,580. Always run
`python3 scripts/verify_model_manifest.py model-manifests/manifest.toml
"$AEGIS_DATA_DIR"` before any acquisition; a pass means do not download
again.

Host-side `MLModel.compileModel` and load passed. The model takes a 416x416 RGB
image plus optional confidence/IoU thresholds and emits coordinates plus
80-class confidence. `person` and `bicycle` labels are embedded. Only Command
Line Tools are installed, so `coremlcompiler` is unavailable; runtime
compilation through Core ML works and is the verified path.

The synthetic detector contract is now executable as
`scripts/run_semantic_detector_contract_gate.sh "$AEGIS_DATA_DIR" OUTPUT.json`.
It passed checksum verification, Core ML compilation/loading, a generated
416x416 input, the `VNRecognizedObjectObservation` result type, provenance and
privacy checks. Zero detections on the featureless color fixture are allowed.
The record is
`docs/experiments/apple-coreml-semantic-detector-contract-2026-07-29.md`.

Next extract a fixed, sparse Old Ghost Road multi-viewport sample pack and run
the same model without tracker initialization. Persist only labels,
confidences, normalized boxes, viewport pose and timing. This is a
person/bicycle recall diagnostic, not a directing or identity claim.

That fixed-five smoke is complete via
`scripts/run_semantic_detector_multiview_smoke.sh`. Timestamps 15, 60 and 210
had no detections; 105 had three `person` detections; 150 had one `person`;
all had zero `bicycle`. Agent contact-sheet inspection found the person boxes
plausible, while the 150-second view visibly contains additional people and
bicycles that were missed. See
`docs/experiments/apple-coreml-semantic-detector-smoke-2026-07-29.md`.

Next initialize the existing Vision tracker from the reviewed 150-second
yaw=-90 person box (`x=0.366455078125`, `y=0.4805908203125`,
`width=0.138671875`, `height=0.498779296875`) over a short forward sequence.
Record loss/continuity without calling the track a bicycle or main character.

Tracking is now tested on two reviewed `person` seeds with detector-matched
416x416 geometry. Both returned 12/12 boxes over three seconds at 4 fps. Agent
contact-sheet review accepts the isolated 105-second person as the same target
but rejects identity continuity in the crowded 150-second riders: persistent
boxes can transfer or ambiguously cover neighboring people. See
`docs/experiments/coreml-seeded-vision-tracking-2026-07-29.md`.

`scripts/run_vision_tracking_gate.sh` now accepts optional trailing
`WIDTH HEIGHT`, defaulting to its original 640x360. Never reuse a normalized
detector box across different projection dimensions without redetection.

Next implement a backend-independent detector-refresh association policy:
same semantic class plus bounded geometry may return compatible, multiple
compatible detections must return ambiguous, and no match must remain missing.
Do not promote geometric refresh to verified identity.

That core policy is implemented in `src/aegis360/detector_refresh.py`.
Synthetic gates cover one compatible person, crowded multiple-person
ambiguity, wrong-class/distant missing evidence and ERP seam proximity.
Compatibility is explicitly not identity verification.

Next build a bounded orchestration artifact that combines detector refresh
events with tracker observations. It must preserve `compatible`, `ambiguous`
and `missing` outcomes, retain model/viewport provenance, and withhold
editorial persistence whenever refresh is ambiguous. Do not render before a
reviewable refresh trace demonstrates that identity is not silently reassigned.

The privacy-safe artifact contract is now implemented in
`src/aegis360/refresh_trace.py`. It preserves compatible, ambiguous and missing
events, model-independent track/class IDs and the configured angular radius.
Every v1 event explicitly denies editorial persistence. Tests cover all three
outcomes, monotonic timestamps and absence of local paths.

Next wire the native detector and tracker outputs into this trace for one
bounded, detector-matched viewport sequence. Do not add planner candidates
until the trace plus a visual audit agree on isolated versus crowded behavior.

That native trace now exists for the isolated 105-second person. First, the
tracking gate was corrected to persist viewport dimensions and derive vertical
FOV from the actual aspect ratio. The old 416x416 v1 artifacts have valid
boxes but invalid spherical pitch/step metrics; use `-v2/`.

At 106 seconds detector and tracker agree on the person, producing compatible.
At 107 seconds the tracker remains visually on that person while the detector
misses it and labels a railing box `chair`, producing missing. Both deny
editorial persistence. Evidence and the visual conclusion are recorded in
`docs/experiments/native-detector-refresh-trace-2026-07-29.md`.

Next map compatible to operational observation and ambiguous/missing to the
existing bounded lifecycle policy. A detector miss must enter grace, not
terminate immediately; wrong-class evidence must never reset a person track.

That mapping is implemented in `src/aegis360/refresh_lifecycle.py`.
Compatible requires a real tracker confidence and restores operational active;
missing and ambiguous enter the existing missing grace; repeated misses
terminate only after the configured limit. None of these states grants
editorial persistence.

The unchanged detector has now run at 108 seconds on the same yaw=-90 416x416
viewport. The v3 Vision artifact preserves 16/16 observations, and visual
inspection shows the tracker and detector person boxes on the same person.
The resulting compatible→missing→compatible sequence recovers within grace;
all events continue to deny editorial persistence. The railing is again
mislabeled `chair`, so `refresh_adapter` now filters by requested class before
geometry conversion. Invalid same-class boxes still fail closed.

The three-event trace was validated at
`/tmp/old-ghost-road-t105-yawm90-person-v3-refresh-trace.json`. Copying it to
the external v3 artifact directory was not completed because automatic
permission review timed out; do not treat the temporary path as durable.
Next build a privacy-safe lifecycle-trace CLI that consumes refresh rows plus
real tracker confidence and explicitly records active→grace→active recovery.

That CLI is now `scripts/build_refresh_lifecycle_trace.py`. Against the v3
evidence it writes
`/tmp/old-ghost-road-t105-yawm90-person-v3-lifecycle-trace.json` with active at
106 (0.9844), missing grace at 107 (0.7383 after configured decay), and active
at 108 (0.7302 from the tracker). Every state denies identity verification and
editorial persistence, and the CLI refuses overwrite. Its input refresh trace
is also temporary, so neither `/tmp` path is a durable dependency.

Next add a bounded timeout trace covering enough consecutive refresh misses to
terminate and confirm the existing policy refuses later revival. This may use
a synthetic privacy-safe refresh fixture; do not claim it as real-media
evidence. If using real media, visually audit the target state first.

That synthetic fixture now passes in `tests/test_refresh_lifecycle.py`: with
two allowed missing refreshes, the third miss terminates with
`missing_timeout`, and a later compatible event raises rather than reviving
the track. This is policy evidence only. Next return to detector coverage:
measure whether the indexed YOLOv3 Tiny model can seed intended benchmark
subjects (especially bicycles) at a bounded sampling cadence. Do not download
or select a replacement model implicitly; use the model manifest process.

That compile-once probe now exists as
`scripts/run_semantic_detector_batch.sh`, with five fixed timestamps per
benchmark under `benchmarks/semantic-gate-timestamps/`. It processes four
equatorial viewports per timestamp. Results: Bellpuig 2/5 person and 0/5
bicycle; Old Ghost Road 2/5 person and 0/5 bicycle; Skiing 1/5 person, one
`skis`, and 0/5 bicycle. The Old Ghost Road host run took 14.95 seconds with
235,945,984-byte maximum RSS.

The initial Skiing run was invalid because FFmpeg consumed the timestamp
loop's stdin and silently skipped the last sample. The corrected runner uses
a dedicated FD, `ffmpeg -nostdin`, and exact processed-count validation; its
Skiing v2 result contains 5/5 samples. Tests lock this contract.

Next compare manifest-eligible replacement detector candidates using primary
model documentation and Apple Silicon feasibility. Do not download weights
until the candidate, license, checksum source and intended gate are recorded.

Primary-source research is recorded in
`docs/research/replacement-semantic-detector-2026-07-29.md`. YOLOX-Tiny is the
next conversion-feasibility candidate because its official Apache-2.0 project
publishes 416×416 COCO weights, 5.06M parameters, 6.45 GFLOPs and 32.8 mAP.
YOLOX-Nano is only a performance fallback. RT-DETR and torchvision detectors
are deferred because their path to validated Core ML object detection is
longer. General PyTorch support in Core ML Tools is not proof that YOLOX decode
or NMS converts correctly.

No YOLOX asset or dependency has been downloaded. Next add a proposed,
not-installed manifest record and a conversion-equivalence protocol with
exact acceptance criteria. Acquisition remains an explicit user action.

The proposed asset now has a non-installed record in
`model-manifests/candidates.toml`; it intentionally has no claimed checksum or
byte size and sets `acquisition_authorized=false`. The frozen conversion gate
is `docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`. It requires
raw-tensor equivalence before decoded boxes, then the unchanged fixed-five
coverage probe. Candidate records must never be passed to the installed-asset
verifier.

Run repository tests and handoff validation, then commit/push this research
checkpoint. The next state-changing step—downloading the exact official
YOLOX-Tiny release asset—requires explicit owner authorization.

Before reaching that boundary, the vendor-neutral comparison contract was
implemented in `src/aegis360/detector_equivalence.py` and
`scripts/compare_detector_equivalence.py`. It enforces the frozen raw tensor
and decoded class/score/box thresholds, fails closed on malformed/non-finite
data and emits no source path or pixels. Synthetic tests cover pass, numeric
failure, class mismatch, invalid shape, NaN and invalid boxes.

After validation and commit/push, no further conversion experiment can run
without acquiring the exact proposed checkpoint and isolated dependencies.
Request explicit authorization rather than downloading implicitly.

The owner authorized acquisition. The official checkpoint is installed and
verified by `model-manifests/manifest.toml`: 40,755,013 bytes, SHA-256
`9de513de589ac98bb92d3bca53b5af7b9acfa9b0bacb831f7999d0f7afaee8f0`.
YOLOX source tag `0.1.1rc0` is fixed at commit
`e1052df71842031413f6030723c3607b839c80ce`. Python 3.12 and two isolated
external venvs were used; normal runtime dependencies remain unchanged.

Strict checkpoint load passes and raw output is `(1, 3549, 85)`. Core ML
default precision fails the frozen gate identically under Torch 2.13 and 2.7
(max error 1.49157, top-20 17/20). FLOAT32 under Torch 2.7/Core ML Tools 9.0
passes zero, mid-gray, both gradients and seeded noise; worst max error is
0.0001833 and every top-20 set agrees 20/20. Evidence is recorded in
`docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`.

Next implement a shared decode/NMS contract frozen at the upstream demo
defaults: confidence 0.25 and NMS IoU 0.45. Validate decoded parity on
generated fixtures before running any benchmark viewport.

The shared decoder is `src/aegis360/yolox_decode.py`; synthetic NMS and
generated decoded parity pass. A source/preprocessing error was found and
corrected: checkpoint-release source 0.1.1 used legacy normalization, while
validated current source 0.3.0 commit
`419778480ab6ec0590e5d3831b3afb3b46ab2aa3` defaults to padded BGR 0–255.
Reject all earlier legacy-preprocessing semantic reports.

The official dog fixture under 0.3/current returns five matching PyTorch/Core
ML detections, including COCO bicycle and dog. The valid Old Ghost Road
150-second yaw -90 viewport passes raw parity but retains zero detections at
confidence 0.25/NMS 0.45; its top candidate is bird at 0.2395. Do not lower the
acceptance threshold after observing this.

Next run the official YOLOX COCO evaluation profile (confidence 0.01, NMS
0.65) as an explicitly diagnostic report to list low-score person/bicycle
proposals. It cannot replace the predeclared acceptance result.

The official-evaluation diagnostic is complete. It returns ten matching
PyTorch/Core ML candidates: seven bird, two clock, one person at 0.01030, and
zero bicycle. Visual audit confirms the low-score person box lands on the
central-right rider in bright yellow shorts; bird/clock are class-confusion
false positives over riders/bikes. The temporary frame was deleted.

Next implement a load-once Core ML-only fixed-five coverage runner using
source 0.3 current preprocessing. Emit separate acceptance (0.25/0.45) and
diagnostic official-evaluation (0.01/0.65) summaries. Never merge the profiles
or reinterpret diagnostic candidates as accepted detections.

The load-once runner is `scripts/run_yolox_coreml_coverage.py` and all three
fixed-five probes are complete. Acceptance counts across twenty viewports:
Bellpuig 7 person/0 bicycle; Old Ghost Road 1 person/1 bicycle; Skiing 7
person/0 bicycle. The accepted Old Ghost Road bicycle is at 60 seconds yaw 0,
score 0.29753, normalized box approximately
`(0.5173, 0.5632, 0.2062, 0.4342)`. Visual inspection confirms the box covers
the bicycle frame/front wheel on the hut porch. The temporary frame was
deleted.

Core ML inference is 0.35–0.41 seconds per twenty viewports, end-to-end
elapsed 7.84–12.70 seconds, and maximum RSS 391,888,896–406,142,976 bytes.
Diagnostic-profile person counts are high and cannot be treated as accepted
recall. Next adapt the Core ML-only decoded rows to the existing semantic
detector contract and seed one bounded Vision bicycle track from the confirmed
60-second box. Preserve class as bicycle but do not claim persistent identity
or main-character status.

Old Ghost Road coverage v2 now retains accepted detection boxes. The
dependency-free `src/aegis360/yolox_seed_adapter.py` converts only in-frame
acceptance person/bicycle detections from top-left to Vision bottom-left
coordinates; low-score diagnostic rows cannot seed.

The confirmed bicycle seeded
`outputs/vision-tracking-gate/old-ghost-road-t60-yaw0-yolox-bicycle-v1/`.
Results: 16/16 tracked over four seconds at 4 fps, zero lost/error, maximum
center step 2.09 degrees, final confidence 0.273. Visual audit confirms the
same bicycle region at 60.00 and 61.75 seconds. At 63.75 a foreground rider
occludes the bicycle and the box mixes bike/rider content. Treat this only as
operational bicycle-region continuity; the temporary contact sheet was
deleted.

Next run low-cadence YOLOX acceptance refreshes at exact tracker timestamps
within this sequence. Feed only class/geometry evidence into the existing
refresh lifecycle; never grant identity or editorial persistence.

YOLOX acceptance refreshes were run at t61/t62/t63. All three contain a
bicycle candidate, but t62 overflows the viewport bottom by approximately
0.00226 normalized units. The strict seed/refresh adapter rejects it and does
not clip. Legal t61 and t63 events are both
`compatible_not_identity_verified`; lifecycle stays active at tracker
confidence 0.936 then 0.432, with identity/editorial persistence false.

Privacy-safe durable traces are
`yolox-refresh-trace.json` and `yolox-refresh-lifecycle.json` beside the
external t60 bicycle tracking artifact. The excluded t62 report remains in
`/tmp` only and is not a durable dependency.

Next evaluate a versioned boundary-tolerance policy using synthetic boxes and
actual projection/rounding error. Do not introduce clipping merely to accept
t62; strict zero tolerance remains current behavior until evidence supports a
bounded alternative.

ADR 0009 accepts an explicit detector edge-repair policy capped at one source
pixel per axis while retaining strict zero as the default. Local YOLOX 0.3.0
source confirms inference postprocessing does not clip boxes. The t62
overflow is 0.9408 pixels at 416x416; repair shifts its center by about 0.113
degrees in the square 100-degree viewport. A separate v4 trace now contains
compatible t61/t62/t63 refreshes, with identity and editorial persistence
still false:

- `yolox-refresh-trace-one-pixel-v4.json`
- `yolox-refresh-lifecycle-one-pixel-v4.json`

Both are beside the external tracking artifact. The original strict trace is
preserved. Both v4 documents explicitly carry
`geometry_policy: one-source-pixel-v1`; unknown policy identifiers fail
closed. Next extend the current three-refresh proof into a bounded longer
sequence before allowing detector refresh evidence into camera planning.

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
- The rejected held-out equatorial-mask comparison is under
  `outputs/source-motion/old-ghost-road-35-40-equatorial-mask-heldout-v1/`.

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
