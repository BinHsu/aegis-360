# Project status

Status: Ready for the first executable evidence slice

The product and architecture decisions needed to begin the POC are recorded.
The agent entry point, documentation index, initial ADR set, design notes,
research ledger, experiment protocols, and three-asset benchmark manifest
exist. The original scaffold is preserved under `docs/archive/` and is not
current authority.

There is no implementation, verified setup command, automated test suite, or
benchmark result yet. No claim about output quality, throughput, memory use,
thermal behavior, model accuracy, or hardware acceleration has been validated
in this repository.

## Next evidence gate

Build the smallest executable vertical slice that can disprove geometry or
rendering assumptions before adding perception models:

1. Add reproducible synthetic fixtures and tests for spherical geometry and
   camera-path continuity.
2. Probe the installed FFmpeg and validate a static, then dynamic, `v360`
   proxy render against those fixtures.
3. Record the exact commands and environment only after they execute
   successfully.

After that gate, acquire the benchmark media explicitly, verify its metadata
and checksum, and implement fixed-forward and greedy-with-hysteresis baselines.
Do not report performance or quality until executable paths and artifacts
exist.
