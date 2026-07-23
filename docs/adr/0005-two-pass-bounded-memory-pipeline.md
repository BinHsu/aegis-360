# 0005: Use a two-pass, bounded-memory pipeline

Status: Accepted

## Context

Full-resolution 360 frames and model activations can exhaust 16 GB unified
memory quickly. Repeating detection and source-resolution rendering for every
planner change would also slow experimentation unnecessarily.

## Decision

Use two principal passes:

1. Analyze a reusable low-resolution proxy with sampled/adaptive perception,
   then cache compact tracks, evidence, candidate shots, and the camera-path
   decision trace.
2. After selecting a plan, stream the source once to render the final output
   while preserving required timing/audio behavior.

All frame pipelines use bounded queues. Do not retain a whole decoded video,
unbounded full-resolution frames, or full-resolution float tensors. Execute
large models in stages when concurrent residency would threaten memory.

## Consequences

- Planner and scoring iterations should use cached analysis and proxy previews.
- Source-resolution render happens only when needed for a chosen path.
- Sequential video/proxy files are preferred over huge collections of frame
  images, especially on external storage.
- Cache schemas and timestamp mappings become explicit interfaces and require
  validation.
- Hardware acceleration remains an implementation option governed by ADR 0004,
  not a requirement of this architecture.
