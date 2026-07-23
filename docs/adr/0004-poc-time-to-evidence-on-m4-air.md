# 0004: Optimize POC time-to-evidence on the available M4 Air

Status: Accepted

## Context

The available development and benchmark machine is a fanless MacBook Air with
an M4 and 16 GB unified memory. Models, benchmark media, caches, and outputs
must live primarily on external storage. The POC exists to test directing
quality quickly, not to establish a product platform or demonstrate a
particular framework.

## Decision

Optimize for credible evidence and iteration speed on this machine. Use a
user-configured external data root for large artifacts; the current local path
must not be hard-coded into versioned files. Cross-platform support is not a
POC concern, and Apple ecosystem lock-in is acceptable.

Apple-specific facilities such as MPS, VideoToolbox, Core ML, the Neural
Engine, or Metal may be used whenever they shorten implementation or benchmark
time. None is mandatory without a measured need. Mature CPU/FFmpeg paths are
acceptable correctness references and initial implementations.

## Consequences

- Portability abstractions, Windows/Linux support, and avoidance of vendor
  lock-in receive no POC effort.
- External storage saves internal disk space but does not increase unified
  memory; model and frame residency must still fit within 16 GB shared by the
  OS, CPU, and GPU.
- Machine-specific paths belong in local environment/configuration, with a
  committed example for forkers and clear failure when the data root is absent.
- Optimize measured iteration blockers rather than implementing Core ML or
  Metal preemptively.
- Sustained behavior matters on a fanless machine, but no performance target is
  asserted before measurement.
