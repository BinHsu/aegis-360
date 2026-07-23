# Project status

Status: First auto-directed vertical slice in progress

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
adapter now produces three decodable, synchronized artifacts from a two-second
synthetic ERP A/V fixture. That synthetic render does not prove real-media
projection, camera behavior or quality. No real 30-second rung has run, and no
viewpoint, motion, editing or viewing quality has been accepted.

## Next evidence gate

Run the smallest real-media vertical slice that can disprove sequence,
directing or rendering assumptions:

1. Use the synthetic-tested FFmpeg render adapter and one immutable
   configuration to create fixed-forward, auto-directed and debug-overlay
   outputs from the same nested real-media 30-second prefix.
2. Validate the artifact bundle, A/V timing, camera-path application and debug
   overlay mechanically before requesting qualitative review.
3. If the 30-second slice is mechanically valid, ask the project owner to
   review framing, obvious camera motion and switch behavior; do not infer
   comfort or quality from synthetic orchestration tests.
4. Advance the unchanged configuration through the 60/180/300-second duration
   ladder only for eligible assets. Use the 300-second Skiing rung for
   sustained performance evidence.

Old Ghost Road is eligible through 180 seconds, Bellpuig through 180 seconds
with its explicit projection override, and Skiing through 300 seconds. Bellpuig
remains a stress test rather than spherical geometry ground truth. Human
candidate review, projection/backend comparison, global planning and a
comfort-threshold decision remain separate follow-ups. Do not report
performance or quality until the corresponding executable path, artifacts and
experiment record exist.
