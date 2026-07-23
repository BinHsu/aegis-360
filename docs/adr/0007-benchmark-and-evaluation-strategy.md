# 0007: Use licensed first-person benchmarks and comparative evaluation

Status: Accepted

## Context

The POC needs first-person movement footage representative of bike, travel,
and action-camera viewing. Public demonstration also requires pre-existing
permission to adapt and redistribute results without obtaining separate
written permission. No single objective viewpoint label captures every
reasonable ordinary-viewer choice.

## Decision

Use these three Wikimedia Commons assets as the initial public benchmark set:

1. **Bellpuig on-board 360**, CC BY 3.0 — high-speed first-person motion,
   travel direction, turns, other riders, and camera stability.
2. **3-mins-in-360 on The Old Ghost Road**, CC BY-SA 3.0 — mountain-bike
   travel, riders, road, scenery, and shot/interest changes.
3. **360 SKIING MAY 2019**, CC BY 3.0 — longer high-speed footage, repetition,
   sustained planning, and future highlight evidence.

The asset manifest, rather than this ADR, will hold exact source/download URLs,
creator attribution, access dates, media metadata, hashes, and public-audio
policy. Media files are acquired explicitly into gitignored external storage
and are never committed or downloaded implicitly by normal tests.

Compare fixed-forward, greedy motion/saliency with hysteresis, and the aegis
global planner. Use objective continuity/motion/event-coverage/resource
metrics together with blind pairwise viewer preference. Multiple viewpoints
may be acceptable.

## Consequences

- Derived Old Ghost Road media must follow CC BY-SA 3.0; code licensing remains
  separate from media licensing.
- CC licenses do not automatically clear privacy, personality, trademark, or
  third-party audio rights; public output policy must address those separately.
- Synthetic assets remain necessary for geometry correctness and CI.
- Benchmark results must report inputs, environment, configuration, and
  artifacts; this ADR asserts no result.
