# Project status

Status: First auto-directed comfort gate rejected; 110/120-degree widening
did not materially reduce motion sickness

The product and architecture decisions needed to begin the POC are recorded.
The agent entry point, documentation index, initial ADR set, design notes,
research ledger, experiment protocols, and three-asset benchmark manifest
exist. The original scaffold is preserved under `docs/archive/` and is not
current authority.

Dependency-free spherical-geometry primitives and 12 unit tests exist. Static
FFmpeg `v360` orientation, pitch, horizontal FOV, seam, and pole-adjacent
conventions pass synthetic regression tests. Timestamped `sendcmd` steps for
yaw, pitch, and FOV also pass with synthetic A/V timing checks. A dependency-
free quintic path interpolator now produces dense seam-aware commands with
analytic velocity, acceleration, and jerk bounds. Multi-segment joins are
verified C2 but not generally C3: exact one-sided metrics expose finite jerk
jumps at interior keyframes. No comfort threshold has been selected or
validated. These results do not establish perceived multi-segment comfort,
real-media quality, throughput, memory use,
thermal behavior, model accuracy, or hardware acceleration.

The three benchmark originals have been explicitly acquired outside Git. Their
source facts, byte sizes, SHA-256 values, and stream probes are recorded in the
manifest. Manual source/container/multi-view validation accepts Old Ghost Road
and Skiing as monoscopic ERP for POC use. Bellpuig remains override-required:
its ERP-like 360 content has unexplained 15:8 stored geometry and must not be
used as geometry ground truth. Content/audio publication review remains
pending.

A fixed-forward renderer passes synthetic A/V regression and produced a local,
decodable 10-second Bellpuig smoke-test proxy outside Git. That run establishes
an executable baseline path, not projection correctness or viewing quality.

A dependency-free greedy-with-hysteresis baseline now consumes normalized
candidate evidence and emits a deterministic, explainable JSON-compatible
decision trace. Behavioral fixtures cover dwell, switch margin, sustained
challengers, deterministic ties, missing-incumbent fallback, and seam-aware
transition distance. It has not yet consumed real perception output or
demonstrated better viewing quality than fixed-forward.

The replaceable perception boundary is executable and synthetic-tested. It
records privacy-safe sample identity, adapter/backend/projection provenance,
spherical candidates, explicit missing signals, and optional weights checksum,
while keeping editorial scoring outside the adapter. A native Swift/Apple
Vision bootstrap gate has now run attention/objectness saliency and human-
rectangle requests on four rectilinear views from one Old Ghost Road frame.
All requests executed; only attention saliency returned candidates at that
timestamp. A fixed five-timestamp, scene-distributed batch subsequently ran
without request errors and recorded privacy-safe candidate counts and
runtime/RSS evidence. The timestamps are not event ground truth, and the
candidates have not been manually reviewed. A local-only review pack now
provides five contact sheets, 20 annotated viewports and an index whose human
recall fields remain explicitly unset. Reviewed recall, projection comparison
and a backend decision do not yet exist.

The project owner has accepted the displayed candidate-box localization as
sufficient for continued POC work. This is a qualitative box-placement gate,
not candidate-level human annotation and not acceptance of recall, viewpoint
choice, narrative interest, or backend quality.

An Apple Vision short-sequence tracking probe now records an externally
initialized box, lost/error state and approximate spherical center continuity
without identity data or editorial scoring. A six-frame synthetic moving-box
fixture returned no tracking observations and is retained as an explicit
negative result. A four-frame Old Ghost Road smoke sequence returned the same
track on all frames with a 1.0 persistence ratio and 3.341532-degree maximum
center step. This single large-box, single-viewport smoke does not establish
identity accuracy, seam handoff, lost-track policy or benchmark tracking
quality.

A manifest-driven batch wrapper can now repeat that bounded probe over
multiple manually selected clips and produce a privacy-safe aggregate report.
The report deliberately excludes local paths and does not turn persistence
into a quality threshold. A backend-independent tracking lifecycle also makes
missing and viewport-exit grace periods, confidence decay, recovery, and
termination reasons explicit. It defines the handoff request boundary only;
cross-viewport association and ERP-seam identity continuity remain unproven.

The same fixed-five Vision JSON now passes through the model-independent
perception contract and confidence-free spherical deduplicator. A privacy-safe
external report recorded 37 raw candidates and 37 clusters: no observations
merged under the current geometric thresholds. This unreviewed result does
not establish that duplicates were absent or that the thresholds are correct.
An optional greedy trace proves contract wiring only: every candidate has
zero utility under an explicit neutral policy, and detector confidence is not
used as editorial interest.

The review annotation schema now records reviewer provenance explicitly.
Human review and `model_assisted` drafts are distinct; the latter require an
explicit non-ground-truth limitation and cannot support human recall
conclusions. Schema v1 is rejected rather than silently assumed human, and
inter-rater agreement remains `not_performed`. No completed annotation was
added by this schema change.

The first bounded auto-directed slice is now wired and synthetic-tested from
Vision sequence JSON through spherical deduplication, deterministic temporal
association, explainable interest signals, greedy planning with hysteresis,
and a sparse camera-path document. Temporal association is geometry/type based,
retains candidates for a bounded missing-frame grace period, and always adds a
forward/context fallback; it is not evidence of identity accuracy or seam
handoff. The current interest model exposes only presence, persistence,
composition and forward prior. It deliberately excludes detector confidence
and does not yet model motion change, novelty, event importance or audio.

The greedy weights, dwell/switch settings and material camera-change threshold
now have a versioned, fail-closed configuration contract. A bounded
orchestrator can atomically persist a privacy-safe trace, resolved config,
camera path and artifact manifest, and can invoke an explicit render-adapter
boundary for fixed-forward, auto-directed and debug-overlay outputs. Tests use
a fake adapter to prove orchestration and artifact contracts. A real FFmpeg
adapter produces three decodable, synchronized artifacts from a two-second
synthetic ERP A/V fixture.

Two real Old Ghost Road 30-second attempts now also exist outside Git. The
first selected the context fallback for all 60 decisions because of a
fallback-scoring bug, fixed in `cbe6d37`. The second selected context for 5
decisions and a track for 55, made one switch, and emitted 40 keyframes. Its
three outputs are complete, decode for 30 seconds, and preserve aligned
audio/video.

The second attempt did not pass the camera-path application gate. Dynamic
FFmpeg `v360` output diverged from an equal static-pose render after repeated
timestamped pose commands. The outputs therefore establish real-media
analysis, planning, bundle creation, decoding and A/V preservation, but not
correct application of the planned camera poses. They are not suitable for
human review; no viewpoint, motion, editing or viewing quality has been
accepted. Privacy-safe artifact-root-relative records are in
`docs/experiments/first-auto-directed-slice.md`; source-media absolute paths
remain unrecorded.

A third attempt reused the same evidence and planning configuration with
`shot_static_v360`. It grouped the decisions into two shots, rendered each
with an explicit static `v360` pose, and concatenated them with audio. All
three outputs decode; auto/debug duration is about 30.04 seconds with about
20 ms video/audio duration difference. Sampled frames no longer show the
repeated-command pose divergence. This opens qualitative review for framing
and cut behavior only; v3 does not validate smooth tracking motion.

The project owner's qualitative review rejected v3. Fixed-forward lost the
bicycle and shook abnormally near the end. Auto-directed also lost the bicycle
and remained uncomfortable despite somewhat less end shaking; the debug
output's ending was worse. The selected track is `attention_saliency`, not a
verified bicycle identity, so the result does not demonstrate identity
continuity. The selected FOV ranged approximately from 44 to 93 degrees, with
a median of approximately 76 degrees. The reviewer identified this relatively
narrow framing as a likely amplifier of viewpoint errors and discomfort. The
30-second qualitative gate therefore failed, and the unchanged configuration
must not advance to 60 seconds.

A follow-up 1920x1080 rectilinear comparison at 110-degree and 120-degree
horizontal FOV produced no significant perceived difference in owner review;
the shaking continued to cause substantial motion sickness. The 120-degree
configuration is recorded in commit `99b266a`, with generated media outside
Git at
`outputs/auto-directed/old-ghost-road-30s-v1/bundle-v4-120deg-1080p/`
relative to the external artifact root. This is negative evidence for FOV
widening as a sufficient remedy, not acceptance of either framing policy.
Do not test a wider rectilinear FOV until the motion source is isolated.

A paired rendered-flat shake probe sampled the v4 110-degree fixed-forward
and auto-directed outputs at 6 fps with 160x90 grayscale proxies. Their
first-window p95 translation steps were 1.75 and 2.81066 pixels. In the last
window, median steps were 2.0 and 2.11803 pixels, p95 steps were 10.25305 and
10.32843 pixels, and p95 translation-vector changes were 5.78208 and 6.60351
pixels, respectively. The nearly equal approximately 10.3-pixel tail p95
steps provide bounded evidence that shared global/source motion dominates the
uncomfortable ending; the auto-directed output does not improve these tail
metrics, and FOV is not the primary remedy. The probe is translation-only and
parallax-sensitive: it cannot isolate roll, perspective rotation, moving
subjects, or causal stabilization quality, and it is not viewer-comfort
ground truth.

An Apple Vision homographic-motion host calibration initially failed because
the correction consumer assumed a simple top-left, current-to-prior sign
rule. The probe now preserves Vision's native matrix convention and the
calibration fixture asserts the empirically observed translation-axis and
rotation signs. Both known-translation and known-rotation fixtures then
passed on the macOS host. This establishes the fixture-to-correction
convention, not camera-motion ground truth.

Calibrated 6 fps motion evidence and stabilization plans now exist for the
last five seconds of the v4 110-degree fixed-forward and auto-directed
renders. The fixed plan reports a 120-pixel conservative symmetric overscan
margin, a 1680x840 centered crop and 119.42 pixels maximum corrected-corner
displacement. The auto plan reports a 360-pixel margin, a 1200x360 crop and
504.55 pixels maximum corrected-corner displacement. The auto plan is
unacceptable: it sacrifices two thirds of the source height and its maximum
corner motion exceeds the reported margin. Privacy-safe artifact-root-relative
records are:

- `outputs/auto-directed/old-ghost-road-30s-v1/motion-fixed-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/stabilization-fixed-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/motion-auto-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/stabilization-auto-last5-v2.json`

Direct measurement of the original Old Ghost Road ERP from 25–30 seconds,
without `v360`, returned motion on all 29 adjacent pairs: rotation-proxy RMS
0.03538 radians, p95 0.07566 and maximum 0.13231. Substantial motion therefore
exists before flat reprojection. ERP and rectilinear homographies are not
directly comparable, so this does not claim reprojection has no perceptual
effect; it rules out the hypothesis that only the flat renderer created the
observed motion.

The first Apple-native fixed-forward five-second post-warp output decoded and
retained audio, but failed the motion gate: median translation-proxy step rose
from 2.83 to 3.61 pixels and p95 vector change rose from 5.25 to 12.12. It is
rejected and is not a review candidate. Stabilization must first pass a
known-motion end-to-end fixture, including sampled-to-output-frame
interpolation, before another real-media attempt.

The planner-to-native-renderer synthetic motion-reduction gate generates known
alternating translation and rotation, plans corrections, and requires the
rendered adjacent-luma motion mean to fall below 65% of the input. In the
approved non-sandboxed macOS execution environment, the mean fell from
42.3061 to 7.0689, a ratio of 0.167, and the gate passed. The same
VideoToolbox preflight returns `-12908` inside the restricted command sandbox
but succeeds in the owner's Terminal and in approved non-sandboxed execution;
this is an execution-environment boundary, not evidence that the host encoder
is busy or broken. Future native-render gates must use the approved execution
path and retain exit 77 for an actual unavailable encoder.

The proposed spherical stabilization and segment-treatment boundary is
documented in
`docs/design/spherical-stabilization-and-segment-policy.md`. It separates
source orientation `R(t)`, stabilized orientation `S(t)`, and director path
`D(t)` for one ERP-to-rectilinear projection. It also keeps editorial value
separate from technical risk. The proposed `action-natural` default and all
thresholds remain unvalidated hypotheses.

The native renderer now interpolates sampled similarity corrections through
translation, shortest-path rotation and logarithmic scale. A 10 fps plan
driving a 30 fps known-motion fixture reduced adjacent-luma motion from
32.8154 to 7.1722, a passing ratio of 0.219. This establishes sampled-plan
interpolation on the synthetic fixture.

The corresponding real fixed-forward last-five-second v2 remained a failure:
median translation-proxy step increased from 2.828 to 3.162 pixels and p95
translation-vector change increased from 5.250 to 11.423 pixels. It decoded
at 1920x1080 for five seconds and retained audio, but it is rejected and must
not be shown as a stabilization candidate. Flat homographic post-warp is no
longer the primary stabilization path; evaluate it only later as a bounded
residual correction after spherical source-motion stabilization.

A dependency-free robust `SO(3)` fit, viewport-pixel-to-world-ray adapter and
privacy-safe multiview source-motion assembler now pass synthetic
yaw/pitch/roll, outlier, invalid-gap and CLI tests. The assembler accumulates
pairwise rotations into `aegis360.source-motion.v1` without source paths or
pixels. This does not yet validate a visual estimator: Vision's native
homography direction and image-axis convention must be calibrated into the
adapter's explicit source-to-target pixel convention before real ERP evidence
is assembled.

The Vision-native homography conversion is now calibrated end to end on
rendered rectilinear fixtures. Vision evidence is explicitly converted from
target-to-source bottom-left coordinates into source-to-target top-left
pixel-center coordinates before ray fitting. Host results recovered yaw 1°,
pitch 2° and roll 3° with maximum tested-ray errors of 0.0164°, 0.0192° and
0.0183°, respectively. A 2.5° yaw trial previously converged to an incorrect
Vision solution, so this gate establishes only a small-adjacent-rotation
operating region; production evidence must reject or resample steps outside a
versioned bound.

The accumulated path now becomes explicitly disconnected after an invalid
pair instead of treating later local deltas as a valid absolute orientation.
Quaternion signs follow the prior sample's hemisphere across 180°, viewport
pitch is bounded to the poles, and non-commuting yaw/pitch accumulation is
covered by tests.

## Next evidence gate

Diagnose and address the failed 30-second qualitative gate before producing a
new review candidate:

1. Establish a gyro-free spherical source-motion path on known ERP
   yaw/pitch/roll fixtures, including high-frequency shake plus a slow
   intentional turn. Fit and smooth one `SO(3)` path, preserve the intentional
   turn, and validate quaternion order before another benchmark render.
   The oracle path, pure rotation fitter and rendered Vision viewport
   direction/sign calibration pass. The next gate is a bounded multiview ERP
   runner that enforces the calibrated per-step rotation range and produces a
   source-motion proxy artifact on a synthetic ERP sequence.

A bounded six-viewport ERP runner and synthetic non-commuting
yaw/pitch/roll fixture are implemented. The versioned scalar step cap is
1.25° (the calibrated 1° yaw step plus 0.25° measurement tolerance), with
additional minimum confidence, inlier-ratio, viewport-coverage and maximum
residual gates. A stricter 0.5° configuration must fail closed. The portable
119-test suite passes. The owner subsequently ran
`tests/test_synthetic_erp_multiview_motion_gate.sh` on the macOS host: all six
samples were measured with finite residuals, no gap was emitted, and the gate
reported `PASS`. This establishes the bounded synthetic ERP-to-multiview
Vision-to-source-motion path; it does not establish real-media estimator
quality or viewer comfort. The next source-motion gate is an analysis-only
five-second Old Ghost Road ERP run with measured gap rate, per-view
contribution, residual, confidence, step angle and sustained resource use.

The first real analysis-only run used Old Ghost Road 25–30 seconds at 12.5
fps. Vision returned observations for all 62 adjacent pairs in all six
viewports, but the fused bounded gate accepted only 2/62 pairs (3.2%).
Forty-four pairs exceeded the 1° residual bound and sixteen exceeded the
1.25° step bound. Median/p95 step angles were 0.816°/1.848° and
median/p95 residuals were 1.253°/1.728°. This rejects 12.5 fps for path
smoothing. The next comparison uses the source rate of 25 fps with unchanged
fit thresholds; failure to materially reduce residual gaps will redirect work
to per-view disagreement and foreground/parallax handling.

The unchanged-bound 25 fps comparison accepted 23/124 pairs (18.5%).
Step-angle failures fell to eleven, but ninety pairs still exceeded the 1°
fused residual bound. Median/p95 step angles improved to 0.525°/1.388° and
median/p95 residuals to 1.115°/1.551°. The run took 74.80 seconds, maximum
child RSS was 283,377,664 bytes, swap decreased by 24 MB during the run, and
macOS reported no recorded thermal or performance warning. Increasing to the
source rate therefore helps but does not make the path usable. The down
viewport's rotation proxy RMS was an outlier at 0.150 radians versus
0.014–0.025 for the other five; the next gate records per-view fits and their
agreement with the fused rotation without changing thresholds.

The repeated 25 fps per-view diagnosis reproduced the same fused result
exactly. All six views returned 124/124 spherical fits, but disagreement was
spatially distributed rather than isolated to the down view: median
per-view-to-fused disagreement was 1.883° back, 1.506° down, 1.099° left,
and only 0.444–0.521° front/right/up. The next gate is therefore robust
view-level consensus or leave-one-view-out diagnosis with per-pair rejected
view identities. Do not solve this by relaxing residual limits or dropping
the down view globally.

Fixed leave-one-view-out evidence now sharpens that result. Omitting back
accepted 66/124 pairs (53.2%) and omitting down accepted 54/124 (43.5%),
versus 23/124 (18.5%) for all six views. Omitting front, right, or up reduced
acceptance to 9.7–12.9%. Even the best fixed omission still failed 58 pairs,
so do not hard-code a five-view rig from this interval. The next gate is a
deterministic per-pair view-consensus selector, validated first against
synthetic corrupted-view fixtures and compared against all existing
baselines without using the acceptance result as an oracle.

The first deterministic per-pair selector used a 1° rotation-medoid radius
and required four views. It passed corrupted-view unit fixtures and the full
synthetic ERP/Vision gate, then accepted 36/124 real pairs (29.0%). All 36
retained subsets passed the existing fit gates, but 88 pairs failed because
only one to three views were inside the radius. It improves on six-view
fusion but is worse than fixed omission of back or down. Do not widen the
radius post hoc. Treat hard-radius medoid selection as a negative baseline
and investigate temporally causal reliability, foreground/near-field
exclusion, or continuous robust view weighting before another real run.

Past-only causal reliability materially improves the same interval to
86/124 accepted pairs (69.4%), exceeding the best fixed omission at 53.2%.
The first 23 pairs are one 0.92-second failure burst; after it, 86/101 pass
(85.1%) and no later failure run exceeds three frames or 0.12 seconds.
Selection counts strongly suppress back (3/124) while dynamically using down
(35/124) and left (97/124). The next gate is a separate causal source-motion
artifact plus an explicit gap policy; do not render from diagnostic rows or
silently interpolate the initial gap.

The classify-only gap policy marks nine later runs (15 total frames) as
bridge candidates and keeps the initial 23-frame boundary gap unbridgeable.
It performs no interpolation. Synthetic known-motion reconstruction with an
angular error gate is required before producing any filled causal path.

Synthetic local-step SLERP passes within 1e-6 radians. The real candidate
fills only the fifteen classified interior steps and leaves the first 23
invalid. Transitions touching interpolation have maximum local-step angular
change 0.432°, below the artifact-wide 1.797° maximum. Next, form an explicit
connected relative-orientation segment beginning at 0.92 seconds; do not
claim or infer the missing initial orientation.

One relative path segment is now available from 0.92–4.96 seconds with 102
samples and an explicit identity-relative anchor. Raw estimated motion has
median/p95 angular speed 10.80°/s and 24.86°/s; scalar jerk proxy p95 is
9,120°/s³. The next gate is quaternion-space `action-natural` smoothing with
synthetic static, slow-turn, high-frequency jitter, and sign-continuity
fixtures before any viewer render.

The 0.35-second `action-natural` quaternion smoother passes static,
sign-continuity, slow-turn, jitter-reduction, and 25° correction-cap fixtures.
On the real relative segment, angular-speed p95 falls 24.86→7.19°/s and
jerk-proxy p95 9,119.6→257.3°/s³ with only 1.40° maximum correction. This
unlocks a synthetic renderer-convention gate, not a comfort claim.

Renderer convention and known-motion host gates pass, but the first real
canonical render loses to fixed-forward on the translation proxy: median step
3.61 versus 2.24 pixels and p95 vector change 11.49 versus 7.75 pixels. A
deliberately inverted diagnostic is worse still, rejecting simple sign
reversal. The 4.04-second fixed/canonical pair now requires human comfort
review; do not call canonical stabilization successful.

The owner subsequently judged fixed-forward less dizzy than canonical.
Canonical `action-natural` v1 is rejected. The next gate is privacy-safe
spatial residual diagnosis by viewport and vertical image band; do not tune
the smoothing horizon around a contaminated source-motion estimate.
2. Separate attention-saliency continuity from bicycle identity continuity;
   do not label the current selected track as subject tracking.
3. Gate later experiments on stabilization, horizon stability, and
   source/global camera-motion diagnosis.
4. Isolate the cause of the end shaking in fixed, auto and debug outputs;
   do not assume rectilinear FOV widening will mask it.
5. Restart at a new 30-second configuration series for any framing, tracking,
   planning or rendering change.
6. Advance to 60 seconds only after a new 30-second qualitative pass. Treat
   smooth tracking motion as untested until a renderer and review explicitly
   establish it.

Old Ghost Road is eligible through 180 seconds, Bellpuig through 180 seconds
with its explicit projection override, and Skiing through 300 seconds. Bellpuig
remains a stress test rather than spherical geometry ground truth. Human
candidate review, projection/backend comparison, global planning and a
comfort-threshold decision remain separate follow-ups. Do not report
performance or quality until the corresponding executable path, artifacts and
experiment record exist.

Spatial diagnosis reproduces causal acceptance and finds a top-to-bottom
median residual increase in front (0.315→0.496°), left (1.017→1.474°), and
down (1.213→1.523°), but not universally in right or up. This justifies an
equatorial-only bottom-third mask hypothesis. Evaluate it against unmasked
causal fitting on a held-out 35–40 second interval, not the development
interval used to formulate it.

The held-out comparison rejects that mask as a default: it marginally lowers
median residual (0.00790→0.00754 rad) but reduces accepted pairs from 121/124
to 119/124 and adds a step-bound failure. Normalized image-bottom is therefore
not a sufficiently reliable foreground/parallax proxy. Preserve the unmasked
causal estimator as the current baseline; do not render or tune the rejected
mask on this interval.

Independent tile-motion selection now has synthetic consensus and geometry
contracts. Apple Vision preserves deliberately divergent motion for generated
640x360 tiles, while 320x180 was unreliable and is rejected. The implied
2x2 parent viewport is 1280x720; measure its bounded acquisition cost and
thermal/memory behavior before integrating it into the six-viewport estimator
or running benchmark footage.

Compile-once generated evidence measured 496/496 tile pairs in 2.295 seconds
(216.2 registrations/s), with about 56.9 MB maximum child RSS, unchanged swap,
and no recorded thermal warning. That supports implementing a bounded
analysis-only integration, but not a realtime or 30-second sustained claim.
Keep tile sequences serial and retain the unmasked causal estimator as the
comparison baseline.

The first 40–45 second real tile diagnostic completed in 54.37 seconds and
355 MB maximum child RSS. Front/left/up accepted 83–94% of pairs, while
back/right/down accepted only 38–40%. Per-viewport three-of-four consensus is
therefore too lossy as a fusion boundary. Preserve its negative result and
test an unchanged-radius strict-majority consensus across all 24 tiles with
explicit multi-viewport coverage.

Global 24-tile fusion accepted 93/124 development pairs with no fit-bound
failure after selection. Evaluate it once on held-out 45–50 seconds against
the unchanged causal baseline. Require global accepted pairs to be greater
than or equal to causal; do not tune the 0.5° radius, thirteen-tile majority,
or four-viewport coverage after observing that interval.

Held-out causal and global both accepted 124/124, so global passes the
predeclared coverage rule. Its median residual is about 2.1x causal, while its
median step is about 16% lower; neither proves motion accuracy. Before any
render, compare unchanged causal against global on the difficult 40–45 second
development interval and retain both failure patterns.

The identical-timestamp development comparison rejects global tiling:
unchanged causal accepted 123/124 while global accepted 93/124. Keep
independent tiles as analysis evidence for spatial disagreement, not the
primary source-motion fusion path. The unchanged causal estimator remains the
candidate for the next bounded path/render gate.

The next gap-free causal candidate also loses to fixed on the screen-space
proxy: equal 1 px median step, but canonical has 2.0 versus 1.0 px p95 step
and 2.65 versus 1.0 px p95 vector change. Do not request owner review or tune
source-motion thresholds again. For the POC, retain raw/fixed treatment and
resume auto-director perception/planning experiments.

Replaying the original 30-second evidence under the corrected persistence
policy gives generic saliency zero editorial persistence, yet one saliency
region still receives 46/60 decisions because equal presence is resolved by
composition and forward prior. The next gate is seam-aware wide group/context
candidate generation, not identity tracking or another render.

Local group/context geometry now passes synthetic gates and yields candidates
on 23/60 replay frames, but the unchanged scorer selects none. Do not weaken
switch hysteresis. Add a named group-coverage signal with synthetic ablation
and a new versioned config before another planning replay or render.

That implementation gate is complete. The optional bounded `group_coverage` signal and
`greedy-group-context-v1.toml` preserve the old config and hysteresis. The v8
replay selects forward context for 6/60 decisions, a local group for 7/60
(3.0–6.5 seconds), and `track:000002` for 47/60. Its 1920x1080, 30-second
static-shot series is mechanically valid at
`outputs/auto-directed/old-ghost-road-30s-v1/`
`bundle-v8-group-coverage-render/`. Auto and debug share the same motion proxy;
their ending motion is comparable to fixed-forward. The next evidence gate is
owner review of contextual usefulness and switch comfort, not another
threshold change.

Owner review subsequently rejected v8: fixed and auto looked nearly identical,
and fixed looked clearer. The renderer-aware audit found that static-shot
aggregation reduced the three actual view changes to 0°, 1.68°, and 2.65°;
none clears the new 8° pre-review perceptibility floor. The old outputs also
used mismatched encoder settings, invalidating direct image-quality comparison.
Fixed and auto now share libx264 fast/CRF 18/yuv420p, and
`scripts/check_render_pre_review.py` fails closed on decoded stream mismatch
or insufficient actual-shot differentiation. The next candidate must pass
that gate and agent visual frame inspection before owner paths are disclosed.

The first semantic detector asset has been explicitly acquired outside Git:
Apple-hosted YOLOv3 Tiny FP16, 17,769,580 bytes, SHA-256
`73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda`.
`model-manifests/manifest.toml` is the canonical inventory and
`scripts/verify_model_manifest.py` prevents redundant or implicit downloads.
Core ML compilation/loading passes on the host and confirms a 416x416 RGB
input, coordinates plus 80-class confidence outputs, and person/bicycle
labels. The next gate remains a synthetic Swift detector contract before
real-media or tracker integration.

Natural-image gates now show three plausible person detections at 105 seconds
and one at 150 seconds, but zero bicycles and no detections at three other
fixed timestamps. A three-second Vision track visually retains an isolated
105-second person; a crowded 150-second track returns 12/12 boxes but does not
prove stable identity. Detector and tracker dimensions must match.
`detector_refresh.py` therefore fails closed: one class/geometry match is only
compatible, multiple matches are ambiguous, and none is missing. The next
gate is orchestration of periodic detection refresh without promoting
compatibility to identity or editorial persistence.

Native refresh orchestration now shows compatible at 106 seconds, missing at
107, and compatible recovery at 108. Visual overlays confirm the tracker
remains on the same person throughout; the detector temporarily misses that
person and repeatedly labels a railing `chair`. Wrong-class detections are
filtered before geometry conversion, so even malformed irrelevant boxes
cannot poison a valid person refresh. The lifecycle adapter sends
missing/ambiguous through bounded grace and requires real tracker confidence
for compatible recovery. The next gate is a privacy-safe lifecycle trace that
materializes the observed compatible→missing→compatible state transition.
That trace now exists via `scripts/build_refresh_lifecycle_trace.py`: real
tracker confidence produces active at 106, decayed missing grace at 107, and
active recovery at 108. Every row denies identity verification and editorial
persistence. The synthetic timeout fixture now passes: two misses remain in
grace, the third terminates with `missing_timeout`, and a later compatible
refresh cannot revive that track. The next perception gate is broader detector
coverage: establish whether the current tiny detector can seed the benchmark's
intended first-person subjects, especially bicycles, or whether a
manifest-indexed replacement model is required.

The compile-once fixed-five coverage probe now spans all three benchmarks.
Person appears at 2/5 Bellpuig, 2/5 Old Ghost Road and 1/5 Skiing timestamps;
Skiing also yields one `skis` label. Bicycle remains 0/5 for every source.
YOLOv3 Tiny therefore remains a pipeline-contract and occasional person-seed
model, not an accepted generic sports-subject detector. Next research a
replacement candidate under ADR 0008 and the model-manifest rules before any
asset acquisition.

Primary-source research selects YOLOX-Tiny as the next conversion-feasibility
candidate: Apache-2.0, official 416×416 COCO weights, 5.06M parameters, 6.45
GFLOPs and 32.8 reported mAP. YOLOX-Nano is the performance fallback; RT-DETR
and torchvision detectors are deferred due to a longer path to validated Core
ML inference. No asset has been acquired. Next prepare a manifest proposal and
a generated-input numerical-equivalence protocol; acquisition still requires
explicit authorization.

The vendor-neutral equivalence checker is now executable. It compares ordered
raw tensor shape/values and decoded class, score and box IoU against the frozen
thresholds, fails closed on invalid numeric output, and writes a path-free
report. Synthetic pass/fail fixtures are covered. Remaining progress requires
the upstream checkpoint and isolated conversion dependencies, so explicit
asset-acquisition authorization is now the next boundary.

The owner authorized and the official YOLOX-Tiny checkpoint was acquired,
checksummed and added to the installed manifest. Strict load passes. Default
Core ML precision fails the frozen raw gate identically under Torch 2.13 and
2.7, while explicit FLOAT32 under Torch 2.7/Core ML Tools 9.0 passes all five
generated fixtures with maximum error at most 0.0001833 and top-20 agreement
20/20. Next freeze and validate the shared decoder at confidence 0.25 and NMS
IoU 0.45 before any real benchmark inference.

The shared dependency-free YOLOX decoder and class-aware NMS now pass
synthetic tests and generated PyTorch/Core ML parity. Source/preprocessing was
corrected to YOLOX 0.3.0 current BGR 0–255; legacy 0.1.1 normalization reports
are rejected. The official dog fixture returns five matching detections,
including bicycle and dog, with near-identical boxes/scores. On the valid Old
Ghost Road 150-second yaw -90 viewport, however, both backends retain zero at
confidence 0.25; the top candidate is `bird` at 0.2395. Next use the official
COCO evaluation profile (0.01 confidence, 0.65 NMS) as a diagnostic only to
inspect whether low-score person/bicycle proposals exist.

That diagnostic finds ten low-score candidates: seven `bird`, two `clock`, one
plausible `person` at 0.01030, and zero `bicycle`. Visual audit confirms the
person box is on a rider while bird/clock labels are confusion on riders and
bikes. PyTorch/Core ML parity remains valid, so conversion is not the cause.
Next run a bounded fixed-five Core ML-only coverage probe using the validated
0.3/current preprocessing and report acceptance and diagnostic profiles
separately.

The load-once fixed-five probe is complete. Acceptance counts are Bellpuig
7 person/0 bicycle, Old Ghost Road 1 person/1 bicycle, and Skiing 7 person/0
bicycle across twenty viewports each. The Old Ghost Road bicycle at 60 seconds
yaw 0 was visually confirmed on the actual bike frame/wheel. Core ML inference
is only 0.35–0.41 seconds per twenty viewports with roughly 392–406 MB maximum
RSS; source decode/reprojection dominates the 7.84–12.70 second total. This is
the first valid bicycle seed but not broad recall. Next integrate the
Core ML-only output into the existing semantic detector adapter and seed a
bounded Vision track from the confirmed bicycle box.

The v2 coverage artifact now persists accepted boxes and the tested seed
adapter performs the YOLOX top-left→Vision bottom-left conversion without
manual arithmetic. The confirmed bicycle seeds a four-second 4 fps Vision
track with 16/16 observations, zero lost/error and 2.09-degree maximum center
step. Visual audit shows stable bicycle-region coverage initially and through
61.75 seconds; a foreground rider occludes the bike by 63.75 and confidence
falls near 0.27. This proves bounded operational continuity, not identity.
Next run low-cadence YOLOX refreshes during the same sequence and require
class/geometry compatibility without allowing diagnostic boxes or identity
promotion.

Acceptance refreshes at t61/t62/t63 all produce bicycle candidates. Strict
geometry rejects t62 because its box overflows the viewport bottom by 0.00226;
the adapter does not clip. Legal t61 and t63 refreshes are compatible but not
identity-verified, and lifecycle remains active with editorial persistence
denied. This demonstrates detector/tracker class-region continuity through
partial occlusion while preserving the fail-closed boundary. Next decide by
evidence whether a versioned subpixel boundary tolerance is justified; until
then strict zero tolerance remains authoritative.

ADR 0009 now accepts an explicit edge-repair policy capped at one actual
source pixel per axis; zero remains the default. The t62 overflow measures
0.9408 pixels at 416x416 and clamping shifts its center by about 0.113 degrees
in the square 100-degree viewport. With that policy explicitly selected, all
three t61/t62/t63 bicycle refreshes associate as compatible while identity
and editorial persistence remain false. Overflow beyond one pixel still
fails closed.

The first load-once detector/tracker sequence covers all 16 Vision
observations from 60.00–63.75 seconds at 4 fps. Thirteen refreshes are
compatible. A 61.75 bicycle box exceeds the explicit policy by only 0.0527
pixel but is correctly rejected at 1.0527 pixels total overflow; the
lifecycle enters grace and recovers at 62.00. At 63.50 and 63.75 YOLOX
accepts a person but no bicycle, so class separation holds and the bicycle
track remains in bounded grace without identity or persistence promotion.
Core ML inference for all 16 frames is 0.287 seconds, total runtime 5.66
seconds, and maximum RSS about 394 MB.

An eight-second extension returns 32/32 Vision boxes but demonstrates why box
continuity is not identity. Intermittent bicycle refreshes recover the
lifecycle through 65.0; misses at 65.25/65.50/65.75 terminate the original
track. Eight later detector events are rejected from that lifecycle, including
a bicycle at 67.0 that would otherwise revive it. Visual inspection shows
multiple stationary bicycles and crossing people in the region, so the old
Vision box is identity-ambiguous. The fail-closed termination is the correct
planner boundary.

The lifecycle-to-candidate adapter now enforces that boundary. On the real
32-frame artifact, the bicycle candidate exists for 23 frames through the
65.50 grace state, is absent at the 65.75 terminal state, and remains absent
for all eight later tracking observations including 67.0. The forward context
remains available. Operational YOLOX/Vision continuity is `GEOMETRIC_ONLY`,
so editorial persistence stays zero even while the candidate is active.

The planning-only greedy diagnostic produces 32 decisions without rendering.
It selects the lifecycle bicycle through the two-frame grace window at 65.25
and 65.50 because hysteresis temporarily favors camera continuity, then
immediately falls back to `context:forward` when the candidate is removed at
65.75. All eight later frames remain forward, including 67.0. Every
persistence component is zero. The trace is
`greedy-planning-trace-v1.json` beside the external eight-second refresh
artifact.

The proposed post-terminal acquisition gate requires two consecutive
compatible detections and always issues a fresh ID. On the real artifact,
67.0 is an isolated bicycle detection followed by a miss, so
`bicycle-yolox-0002` is not acquired and the planner remains on forward
context. The privacy-safe result is `new-track-acquisition-v1.json` beside the
eight-second artifact. This threshold remains experimental, not an ADR.

The second real sequence reaches the same conservative result. The
105-second isolated-person track later drifts by up to 23.63 degrees; YOLOX
starts a lifecycle only after two compatible detections at 108.0/108.25,
terminates it at 109.0, and sees only one post-terminal person at 109.25.
No fresh track is acquired. Visual review shows two people in all four sampled
frames, confirming that repeated class/geometry evidence remains nonidentity.
The two-confirmation threshold therefore stays proposed.

The proposed gate now also has time bounds: compatible evidence must span at
least 0.25 seconds and adjacent confirmations may be at most 1.0 second apart.
This prevents high-cadence instantaneous acquisition and low-cadence stale
evidence from sharing the same count semantics. Time-bounded v2 traces for
both real sequences still acquire no fresh track; each has only one isolated
post-terminal compatible event.

A single-stream detector cadence runner now keeps one FFmpeg rawvideo pipe and
one loaded Core ML model while preserving the 416×416 BGR and formal YOLOX
confidence/NMS contract. On the same Old Ghost Road 60–68-second, 32-frame
workload it reduces stream processing wall time from 10.551 to 2.249 seconds
(about 4.69×). A 120-frame, 30-second run sustains 16.14 fps with about 365 MB
peak RSS, versus the required 4 fps analysis cadence. Pure-Python YOLOX
decode/NMS is now the measured dominant component at 4.528 of 7.433 seconds;
Core ML uses 2.575 seconds and all remaining stream work 0.330 seconds.
Thirty seconds does not establish fanless thermal stability, and host thermal
and swap values were unavailable in this run. Next freeze decoder outputs and
test vectorized decode/NMS equivalence before optimizing projection or Core ML.

That equivalence gate now passes on all 32 real Core ML frames: detection
count, class, source index, score and box remain within the frozen `1e-6`
contract. The NumPy candidate reduces 120-frame decode/NMS from 4.528 to 0.076
seconds and total stream wall from 7.433 to 2.172 seconds, reaching 55.25 fps
with the same 46 person-positive and 15 bicycle-positive frames. NumPy remains
optional in the isolated Core ML environment; the dependency-free reference
is unchanged. The next performance gate is 180 or 300 seconds with
host-visible thermal, swap and power-state sampling.
