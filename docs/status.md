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
analytic velocity and acceleration bounds. These results do not establish
multi-segment jerk comfort, real-media quality, throughput, memory use,
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

## Next evidence gate

Build the smallest executable vertical slice that can disprove geometry or
rendering assumptions before adding perception models:

1. Add multi-segment path constraints and measure angular velocity,
   acceleration, and jerk at planner transitions.
2. Resolve or explicitly normalize Bellpuig's non-2:1 projection ambiguity.
3. Implement the greedy-with-hysteresis decision-trace baseline on validated
   benchmark inputs.

After that gate, compare the greedy decision trace with fixed-forward and begin
the first perception-adapter spike. Do not report performance or quality until
the corresponding executable path and artifacts exist.
