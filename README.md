# aegis-360

An offline 360-video auto-director experiment.

Given a monoscopic equirectangular video, aegis-360 aims to decide what an
ordinary viewer is most likely to want to see, plan a coherent virtual-camera
path, and export a normal rectilinear video without requiring the user to pick
a subject or add keyframes.

## Why

360 cameras capture every direction, but defer composition until after the
recording. Existing tools provide pieces of the workflow—manual reframing,
selected-subject tracking, automatic framing, or mobile auto-editing—but we
have not found a mature open-source desktop pipeline that combines
camera-agnostic equirectangular input, offline analysis, autonomous viewpoint
selection, and globally planned camera motion.

This repository is a proof of concept. Its first goal is **Full Story**:
preserve chronology and most content while choosing the viewing direction
automatically. Highlight selection and aggressive removal of uneventful
footage come later.

## Current status

Documentation and feasibility planning. There is no working processing
pipeline yet and no benchmark result has been produced.

See [`docs/README.md`](docs/README.md) for the documentation index and
[`docs/status.md`](docs/status.md) for the current acceptance gate.

## Reference environment

The POC is developed and measured on a fanless MacBook Air M4 with 16 GB
unified memory. Models and media live outside the repository under a local
`AEGIS_DATA_DIR`. Cross-platform work is not part of the POC; Apple-specific
tools may be used whenever they shorten time-to-evidence.

Copy `.env.example` to `.env` and set an absolute local data path. No command
should download models or media implicitly.

## Benchmarks

The planned public benchmark uses three openly licensed moving 360 videos:

- Bellpuig on-board 360 — CC BY 3.0
- Old Ghost Road mountain biking — CC BY-SA 3.0
- 360 Skiing May 2019 — CC BY 3.0

The media is not committed to Git. Sources, attribution, licensing, and
eventual checksums live in [`benchmarks/manifest.toml`](benchmarks/manifest.toml).

## License

The intended code license is Apache-2.0. External code, model weights,
datasets, footage, audio, and generated media retain their own licenses.
