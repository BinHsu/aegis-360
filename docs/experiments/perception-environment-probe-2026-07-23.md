# Perception environment probe — 2026-07-23

Status: Observed environment; backend recommendation remains provisional

## Question

Which already-available runtime gives the shortest path to a useful first
perception result on the reference M4 Air without silently installing packages
or downloading weights?

## Run identity

- Date: 2026-07-23 (Asia/Taipei)
- Commit inspected: `4ef9b7e`
- Machine class: MacBook Air `Mac16,12`, Apple M4, 10 CPU cores, 8 GPU cores,
  16 GB unified memory
- OS: macOS 26.5.2 (build 25F84), arm64
- Python: Homebrew CPython 3.14.4 at `/opt/homebrew/bin/python3`
- FFmpeg: Homebrew FFmpeg 8.1.1
- Network/package/model acquisition: none
- Media input: none; this was a capability probe, not a quality or performance
  run

Hardware identifiers such as serial number, hardware UUID and provisioning
identifier were deliberately omitted.

## Observed facts

The active Python is not a virtual environment. No repo-local Python
environment was found. `uv` and `pyenv` executables are installed.

Python module discovery and installed-distribution metadata reported:

| Module | Available in active Python | Observed version |
| --- | --- | --- |
| Pillow | yes | 12.2.0 |
| NumPy | no | — |
| OpenCV (`cv2`) | no | — |
| PyTorch / torchvision | no | — |
| Ultralytics | no | — |
| ONNX Runtime | no | — |
| MLX | no | — |
| Core ML Tools | no | — |
| PyAV | no | — |
| SciPy / scikit-image | no | — |

This says only what is installed in the active interpreter. It does not prove
that a package lacks compatible wheels or cannot be installed in a separate
environment.

The operating system contains Vision, Core ML, Metal, VideoToolbox and
Accelerate frameworks. The system hardware profile reports Metal support.
Apple Swift 6.3.3 and `swiftc` are available from Command Line Tools. A
temporary Swift source importing Vision, Core ML, Metal and VideoToolbox
compiled and ran successfully (`compile_rc=0`, `run_rc=0`). In that process,
`MTLCreateSystemDefaultDevice()` returned no device even though the hardware
profile reports Metal support. That discrepancy may be caused by the execution
environment and must be resolved before relying on direct Metal access. No
Vision/model inference or compute-placement measurement was performed.

The installed FFmpeg:

- advertises `videotoolbox` as a hardware acceleration method;
- provides H.264, HEVC and ProRes VideoToolbox encoders;
- provides software H.264, HEVC, VP8 and VP9 decoders and accepts
  VideoToolbox hardware acceleration through FFmpeg's device path;
- provides `v360`, `scale_vt`, `transpose_vt`, `scale`, `fps`, `select` and
  `sendcmd`;
- is built with arm64 NEON and supports `libx264`/`libx265`.

Filter presence is not evidence of an end-to-end zero-copy graph. In
particular, `v360` is a CPU filter unless a later measured implementation
proves otherwise. Framework presence also does not prove that Vision or a Core
ML model executes on the Neural Engine.

## Recommendation for the first evidence slice

Run a small native Swift/Apple Vision spike as the first perception-backend
gate, behind the task-level interface required by ADR 0008. Start with
attention-based saliency and human rectangles, then add Vision object tracking
only after single-frame outputs are useful. This route needs no Python
dependency stack, model-weight download, or third-party runtime license and is
therefore the shortest currently observed path to test offline perception on
this machine. Do not call it the selected backend until a real frame completes
and runtime/resource behavior is recorded.

Treat this as a bootstrap backend, not a product or quality decision. Built-in
Vision signals do not supply the broad object vocabulary eventually wanted by
the interest model. If reviewed benchmark excerpts show inadequate candidate
recall, the next controlled comparison should create a separate, pinned
Python environment (prefer an interpreter version supported by the selected
backend), then test a PyTorch/MPS or Core ML detector. Package and weight
acquisition must be explicit and separately license-reviewed.

## Recommended proxy and projection strategy

Keep one sequential, timestamp-preserving low-resolution ERP proxy rather than
an image directory. A useful starting configuration to measure, not yet an
accepted default, is:

- 960x480 ERP;
- 2 analysis samples per second during ordinary footage;
- adaptive denser sampling around motion/novelty changes;
- H.264 proxy with source timestamp mapping retained in compact metadata.

Use the ERP proxy directly for inexpensive motion, novelty and forward-motion
signals. Run Vision first on overlapping rectilinear horizon viewports rather
than claiming that natural-image requests work on distorted ERP pixels. Start
with four yaw centers separated by 90 degrees, approximately 100-degree
horizontal FOV, at 640x360. Add tilted/polar views or hybrid refinement only
when manual review shows missed events. Deduplicate viewport observations in
spherical coordinates.

The dimensions, sampling rate, viewport count and FOV are hypotheses for the
existing projection experiment. Fix reviewed excerpts and acceptance
thresholds before selecting them.

## Why not select the other backends yet?

- Ultralytics/PyTorch, ONNX Runtime, MLX and Core ML Tools are not installed;
  selecting one now would first require an explicit environment and model
  acquisition step.
- Python 3.14 package compatibility was not tested and must not be assumed.
- A custom Metal renderer or Core ML conversion has no measured blocker to
  justify its implementation yet.
- CPU FFmpeg remains the projection correctness reference. VideoToolbox is
  immediately useful for proxy encode/decode experiments, but it is not itself
  a perception model.

## Limitations and next gate

This probe did not measure latency, sustained thermals, peak RSS, swap,
candidate recall, tracking continuity, model accuracy, VideoToolbox decode
behavior, or actual CPU/GPU/ANE placement. It therefore unlocks only the
bootstrap implementation choice.

Before promoting any backend or projection strategy, run the existing
perception projection comparison on manually reviewed excerpts and record
quality, elapsed time, peak RSS, swap, artifacts and exact runtime/model
identity.
