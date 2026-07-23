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

## Next evidence gate

Diagnose and address the failed 30-second qualitative gate before producing a
new review candidate:

1. Establish a gyro-free spherical source-motion path on known ERP
   yaw/pitch/roll fixtures, including high-frequency shake plus a slow
   intentional turn. Fit and smooth one `SO(3)` path, preserve the intentional
   turn, and validate quaternion order before another benchmark render.
   The oracle path and pure rotation fitter pass; the next gate is a rendered
   viewport fixture that calibrates Vision homography direction/sign into
   spherical ray matches.
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
