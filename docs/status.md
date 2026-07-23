# Project status

Status: First executable evidence slice in progress

The product and architecture decisions needed to begin the POC are recorded.
The agent entry point, documentation index, initial ADR set, design notes,
research ledger, experiment protocols, and three-asset benchmark manifest
exist. The original scaffold is preserved under `docs/archive/` and is not
current authority.

Dependency-free spherical-geometry primitives and 12 unit tests exist. A
synthetic 20-frame ERP fixture can be rendered through the installed FFmpeg
`v360` filter at two static yaw values; both outputs decode and differ. These
results do not establish absolute orientation, dynamic camera control,
real-media quality, throughput, memory use, thermal behavior, model accuracy,
or hardware acceleration.

## Next evidence gate

Build the smallest executable vertical slice that can disprove geometry or
rendering assumptions before adding perception models:

1. Add image-based orientation, FOV, seam, pole, and black-gap assertions that
   connect the internal geometry convention to FFmpeg `v360` output.
2. Determine and test a timestamped dynamic yaw/pitch/FOV control path while
   preserving timestamps and audio.
3. Record the exact commands and environment only after they execute
   successfully.

After that gate, acquire the benchmark media explicitly, verify its metadata
and checksum, and implement fixed-forward and greedy-with-hysteresis baselines.
Do not report performance or quality until executable paths and artifacts
exist.
