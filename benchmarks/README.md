# Public benchmark media

The initial benchmark set covers fast on-board motion, mountain-bike travel
storytelling, and long-form skiing. Media is external data and is not committed
to this repository.

One supplemental held-out asset, Gaudeamus Igitur, covers fixed-camera group
composition with standing choir rows and seated audience at distinct vertical
positions. Its `[30,38)` second window tests group retention and vertical
composition only; it is not active-speaker evidence. Its derivatives are
CC BY-SA 4.0 and must not be published under a less restrictive media license.
Its source-specific, checksummed geometry lives in
`view-grids/gaudeamus-performance-reaction-v2.json`; it is review evidence, not
a generic camera default.

Source-specific candidate visibility and comparative reaction decisions live
under `candidate-availability/` and `reaction-view-gain/`. These configs bind
human review evidence; they are benchmark labels, not universal thresholds or
an automatic editorial model.

Closed story-role configs live under `scene-story-labels/`. Their README states
whether provenance is owner, agent or model; never promote agent source-context
review to owner ground truth.

Segment-scoped direction labels live under `segment-view-labels/`. They include
explicit abstentions when one stable primary cannot be justified.

Set an external data root before acquisition or processing:

```sh
export AEGIS_DATA_DIR=/path/to/aegis-data
```

Do not encode a developer's absolute path in scripts, manifests, logs, or
decision traces. Acquisition will be an explicit future command; tests must not
download these files automatically.

## Set

- Bellpuig on-board 360 — CC BY 3.0. High-speed on-board motion and a
  non-exact-2:1 input that must be projection-validated.
- Old Ghost Road — CC BY-SA 3.0. Edited 360 mountain-bike travel story with
  multiple mounts; derivatives must satisfy ShareAlike.
- 360 Skiing May 2019 — CC BY 3.0. Long 5K 2:1 moving-sports footage.
- Gaudeamus Igitur — CC BY-SA 4.0. Supplemental non-ego, vertically layered
  group-composition evidence; selected window `[30,38)` seconds.
- Hundra knektars marsch på Forum Vulgaris — CC BY-SA 4.0. Supplemental
  cross-scene reaction evidence with a moving adult procession and stationary
  spectators; candidate window `[217.5,226.5)` seconds. Incidental minors in
  the crowd are not eligible subjects.

The reference-machine acquisition was verified on 2026-07-23. The manifest
records the original download URLs, exact byte sizes, SHA-256 values, and
`ffprobe` metadata measured from those files. A fresh checkout does not contain
the media or an implicit acquisition command; independently acquired files
must match the manifest before use.

Projection validation combines source evidence, stream/container inspection,
and manual multi-timestamp `v360` review; it is never inferred from a 2:1
aspect ratio or filename. Old Ghost Road and Skiing are manually verified as
monoscopic ERP for POC use. Bellpuig is confirmed as ERP-like 360 content but
requires an explicit override/normalization decision because its 15:8 stored
geometry is unexplained. See
`docs/experiments/benchmark-projection-validation.md`. Review faces, logos,
performances, and audio before publishing derived media.

Compare fixed-forward, greedy motion/saliency with hysteresis, and the aegis
global planner. Keep Full Story evaluation separate from aggressive Highlights
evaluation.

The nested duration-ladder protocol is recorded in
`duration-ladder.toml`: all runs begin at the same timestamp and reuse one
configuration, with fixed-forward, auto-directed, and debug-overlay outputs.
Asset length permits 30/60/180 seconds for Bellpuig and Old Ghost Road, and
30/60/180/300 seconds for Skiing.
