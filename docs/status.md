# Project status

Status: First executable evidence slice in progress

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

## Next evidence gate

Build the smallest executable vertical slice that can disprove geometry or
rendering assumptions before adding perception models:

1. Use the measured multi-segment derivative discontinuities to decide whether
   the first planner needs a coupled spline, while avoiding an unevidenced
   comfort threshold.
2. Resolve or explicitly normalize Bellpuig's non-2:1 projection ambiguity.
3. Define the first replaceable perception adapter and produce normalized
   candidate observations for a short validated benchmark segment.

After that gate, feed those observations to the greedy baseline and compare its
decision trace with fixed-forward. Do not report performance or quality until
the corresponding executable path and artifacts exist.
