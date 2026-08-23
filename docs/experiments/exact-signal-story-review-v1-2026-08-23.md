# Exact-signal story review packets v1

## Problem

Old Ghost Road has 25 fused events but 26 retained scene-change signals. Event
`event:multi:0002` contains boundaries at 24.5 and 25.9 seconds. The earlier
event-scoped packet samples before the first and after the last, so one label
cannot say which exact signal starts a chapter.

## Contract and result

`aegis360.scene-boundary-story-review-packet.v1` binds one exact event ID,
signal ID and timestamp. It retains the bounded six-anchor policy at ±15,
±3 and ±0.25 seconds, with four declared cardinal views per composite and no
durable pixels. The transient runner validates the new schema, renders at most
six composites and deletes its media after adapter completion.

The external Old Ghost Road run produced 26 path-free JSON packets, each with
six samples. The manifests live under
`outputs/scene-boundary-story-review-packets/old-ghost-road-pyramid-v1/` and
contain no pixels. A temporary 26-cell before/after storyboard was visually
inspected only as a coarse chapter screen; it was not retained as evidence and
is insufficient to qualify the final chapter map.

Two packet tests prove exact fused-signal scoping, boundary anchors, review-job
compatibility, missing-signal failure and exact-rebuild mutation rejection.
This closes packet coverage, not semantic labeling: 21 signals still need
source-context dispositions before a complete experimental map can be built.
