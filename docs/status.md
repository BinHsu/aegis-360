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
yaw, pitch, and FOV also pass with synthetic A/V timing checks. These results
do not establish smooth camera paths, real-media quality, throughput, memory
use, thermal behavior, model accuracy, or hardware acceleration.

The three benchmark originals have been explicitly acquired outside Git. Their
source facts, byte sizes, SHA-256 values, and stream probes are recorded in the
manifest. Projection validation and content/audio publication review remain
pending.

## Next evidence gate

Build the smallest executable vertical slice that can disprove geometry or
rendering assumptions before adding perception models:

1. Convert planner keyframes into a seam-aware, smooth per-frame camera path
   and test angular velocity, acceleration, jerk, and command timing.
2. Validate the projection of each benchmark asset before treating it as ERP.
3. Produce low-resolution fixed-forward proxies without silently publishing
   or redistributing the source media.

After that gate, implement the greedy-with-hysteresis baseline and compare its
decision trace with fixed-forward. Do not report performance or quality until
the corresponding executable path and artifacts exist.
