# Multi-signal timeline and review packet v2

Status: Executed on 2026-08-16

## Question

Can neutral scene-change boundaries enter the sparse semantic hierarchy
without inheriting reaction roles or exceeding the M4/16 GB review bound? A
pass unlocks semantic labeling of new events. It does not establish importance,
select a view or select a model.

## Timeline contract

`aegis360.event-timeline.v2` converts each cheap signal to a bounded review
window and clusters overlapping windows. Original signal IDs and evidence
remain inside the fused event. Reaction-only clusters retain their declared
current/proposed scope and availability. Any cluster containing scene-change
evidence uses every declared context candidate because scene score carries no
direction or role.

The initial fusion policy uses two seconds before and after each scene boundary
and merges overlapping review windows. The artifact binds exact grid,
scene-candidate and optional reaction-timeline hashes. A missing reaction input
is explicit null provenance, not an empty fabricated result.

## Review packet contract

`aegis360.event-review-packet.v2` uses two timestamps for a neutral boundary:
the fused window's start and end, each across all four cardinal candidates.
This produces eight silent render jobs, below the existing maximum of ten.
Role-pair events retain a five-anchor schedule with proposed views included
only inside declared availability. Unknown modes, reordered grid candidates
and more than ten jobs fail closed.

The transient-media runner now exact-validates packet v1 or v2 before resolving
grid-owned geometry. It continues to invoke adapters without a shell and
deletes all rendered pixels after adapter exit.

## Old Ghost Road execution

Environment: fanless M4 MacBook Air, 16 GB unified memory; macOS 26.5.2;
FFmpeg 8.1.1; no model or network.

The 225.453-second source used a deterministic four-cardinal grid. Nine
scene-change candidates produce nine nonoverlapping four-second events at
41–45, 51–55, 82.5–86.5, 93.5–97.5, 107.5–111.5, 119.5–123.5,
161.5–165.5, 191.5–195.5 and 220–224 seconds. Every event retains all four
candidate IDs and no editorial role.

External artifacts:

- grid SHA-256 `26b869dd733a9b201c6a37526d37af7bdd08e4c316fefc650ede7876efbfbf1f`;
- timeline SHA-256 `e1e3c78a76a80b30ec40f7953830deaaeca556983b12b2202bf247e31a638065`;
- `outputs/event-review-packets/old-ghost-road-multi-signal-v2/` contains nine
  packet manifests, each declaring eight render jobs and an independent hash.

A real v2 runner smoke test rendered all eight nonempty frames for event 0000,
the diagnostic adapter matched its index, and the reported temporary directory
was absent after exit.

## Limitations and conclusion

V2 currently fuses only scene-change and reaction signals. The Old Ghost Road
run contains scene signals only, so it does not exercise real mixed-event
fusion. Two before/after timestamps may miss short activity inside a window.
The grid is coverage geometry, not proof that every direction is useful.

The contract passes its narrow gate. Visually pre-review the neutral packets,
discard change caused only by shake/exposure, then request owner labels only
for the surviving bounded set. Do not acquire or tune a model first.

## Owner-review bundle preparation

Agent review of all nine before/after cardinal contact sheets separates clear
edits from within-scene motion. Three representative four-second silent 2x2
cardinal videos were rendered with identical libx264 fast/CRF 18 settings:

- event 0001, boundary case (group/ridge to scenic travel), video SHA-256
  `1360c7b9d8bca78b2c0e7dac21db903abf0006ff6a7c6d46b1c2c235469bf099`;
- event 0002, clear positive (hut exterior to interior), video SHA-256
  `a03a2047facf6db80b5fffe92929993e86a5bcecf991c88d626ac5d25e776e8e`;
- event 0006, within-scene motion case (forest/rider passage), video SHA-256
  `49ba66d180d48af1104b7f586c2acb64a524e108e8a81d939982a25cd4c12039`.

All are H.264 1280x720, 4.000 seconds, 100 frames and contain no audio stream.
Their path-free traces bind timeline, grid and packet hashes. A second
time-series contact-sheet inspection found the transitions perceptible and no
obvious blocking, blur or projection defect. Temporary audit pixels were
deleted. These three now require owner ground-truth labels before semantic
adapter evaluation continues.
