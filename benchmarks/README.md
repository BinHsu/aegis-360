# Public benchmark media

The initial benchmark set covers fast on-board motion, mountain-bike travel
storytelling, and long-form skiing. Media is external data and is not committed
to this repository.

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

The reference-machine acquisition was verified on 2026-07-23. The manifest
records the original download URLs, exact byte sizes, SHA-256 values, and
`ffprobe` metadata measured from those files. A fresh checkout does not contain
the media or an implicit acquisition command; independently acquired files
must match the manifest before use.

Projection remains pending where the containers do not provide authoritative
projection metadata. Never infer it from a 2:1 aspect ratio or filename. Review
faces, logos, performances, and audio before publishing derived media.

Compare fixed-forward, greedy motion/saliency with hysteresis, and the aegis
global planner. Keep Full Story evaluation separate from aggressive Highlights
evaluation.
