# ADR 0010: Sparse event-level semantic planning

Status: Accepted
Date: 2026-08-16

## Context

The product goal is one-click automatic directing of a complete 360 video. A
temporary reaction experiment reduced one decision to a human-authored or
local-VLM `promote`/`abstain` comparison. That boundary exposed useful safety
requirements, but making the user approve isolated events would contradict the
product goal. Asking a vision-language model to inspect every frame would also
duplicate cheaper perception, increase memory/thermal cost on the M4 Air, and
still omit the temporal context needed for directing.

Gaudeamus and Hundra demonstrate the missing context. Applause justifies an
audience cut after a staged performance, while the first-person procession's
current view already presents the reacting crowd. The installed SmolVLM2 2.2B
model abstained on both isolated pairwise comparisons, so that adapter cannot
distinguish the accepted positive from the held-out negative.

## Decision

Build the automatic director around a sparse, whole-video semantic hierarchy:

1. Stream inexpensive signals across the complete proxy: audio events,
   detections/groups, tracking state, motion changes, scene changes and
   candidate-view availability.
2. Merge those signals into a checksummed, path-free event timeline.
3. At sparse event boundaries, generate bounded review packets containing
   before/during/after context, current view, declared candidate views and
   machine evidence. Do not sample a VLM on every frame.
4. Let a replaceable local semantic adapter emit closed event-level evidence,
   including abstention. It cannot create geometry, identity or candidates.
5. Let the explainable global planner—not the model—combine event value with
   chronology, dwell, repetition, transition and camera-motion costs.
6. Use human judgments only as benchmark ground truth and acceptance evidence,
   never as a required product execution step.

The first implementation milestone is `aegis360.event-timeline.v1`, initially
normalizing existing Gaudeamus and Hundra reaction evidence without inventing
new model claims. Event review packets and model selection follow the timeline
contract.

## Consequences

- The POC remains an automatic end-to-end product investigation rather than a
  human-in-the-loop editor.
- Cheap full-video analysis and sparse semantic review fit the fanless M4/16 GB
  constraint better than per-frame VLM inference.
- Candidate availability, relative-gain labels and reaction pre-review remain
  useful evidence and regression gates, but are not the product interface.
- A model cannot directly command the renderer; global planning retains final
  authority and a deterministic abstention path.
- Human labels must be accumulated across more events before selecting or
  tuning another semantic model. Two labels are not an accuracy dataset.
- Event-timeline correctness and information loss become explicit testable
  risks before model quality or global-planner optimization.

## Rejected alternatives

- Require the user to approve every `promote`/`abstain` decision: contradicts
  one-click directing and turns benchmark labels into product workflow.
- Run a VLM on every frame: wasteful, thermally inappropriate and lacking an
  explicit event hierarchy.
- Continue prompt-tuning SmolVLM2 2.2B on the two reviewed cases: risks encoding
  benchmark answers and does not repair missing temporal context.
- Let a VLM output camera geometry or renderer commands: violates geometry
  ownership, explainability and fail-closed planning boundaries.
