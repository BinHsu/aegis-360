# YOLOX Core ML single-stream cadence — 2026-07-30

Status: Completed bounded cadence comparison; not a thermal-duration gate

## Question and decision

Does the existing 4 fps detector-refresh runner spend its time in Core ML, or
in repeatedly seeking, launching FFmpeg, and transferring frames? If process
startup dominates, analysis should use one bounded FFmpeg raw-video stream
with one loaded model.

The decision was fixed before measurement: retain the single-stream design if
it preserves the existing 416×416 BGR, confidence 0.25 and class-aware NMS
0.45 contracts, delivers at least 4 fps, remains below the repository's 10 GB
RSS target, and persists no pixels or source paths.

## Configuration

- Repository baseline: `0a28ec9`.
- Hardware: fanless Apple Silicon MacBook Air M4, 16 GB unified memory.
- OS: macOS 26.5.2 build 25F84.
- FFmpeg: 8.1.1, one process, `v360` linear interpolation.
- Source: Old Ghost Road, SHA-256
  `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`.
- Model: official YOLOX-Tiny 0.1.1rc0 checkpoint converted explicitly to
  FLOAT32 with Core ML Tools 9.0/Torch 2.7.0; upstream checkpoint SHA-256
  `9de513de589ac98bb92d3bca53b5af7b9acfa9b0bacb831f7999d0f7afaee8f0`.
- Python: 3.12.13 in the external isolated conversion environment.
- Viewport: yaw 0°, pitch 0°, horizontal FOV 100°, 416×416 BGR24.
- Cadence: 4 fps. Intervals: 60–68 seconds and 60–90 seconds.
- The model is loaded once. Frames travel through a bounded rawvideo pipe and
  are not written to disk or retained after inference.

Thermal and swap queries were attempted after the runs. `pmset -g therm`
returned no available thermal/performance warning level, and sandboxed
`sysctl vm.swapusage` was denied. These values are therefore unmeasured, not
assumed healthy. Thirty seconds is a sustained-cadence check, not the planned
three-to-five-minute thermal gate.

## Results

The final v3 runner uses the repository's actual `decode_yolox` and
class-aware NMS, with postprocessing timed separately.

| Interval | Frames | Stream wall | Throughput | Core ML | Decode/NMS | Residual wall | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 s | 32 | 2.249 s | 14.23 fps | 0.753 s | 1.239 s | 0.257 s | 381,026,304 B |
| 30 s | 120 | 7.433 s | 16.14 fps | 2.575 s | 4.528 s | 0.330 s | 364,625,920 B |

The previous exact-timestamp 8-second refresh runner processed the same 32
samples in 10.551 seconds, including 0.618 seconds of Core ML inference and
414,203,904 bytes peak RSS. The single-stream v3 therefore reduces stream
processing wall time by about 4.69× while preserving the detector decode
contract. It exceeds the required 4 fps cadence by 3.56× in the shorter run
and 4.04× over 30 seconds.

In the 30-second run, Python YOLOX decode/NMS consumes 60.9% of stream wall,
Core ML inference 34.6%, and the residual 4.4%. The residual includes FFmpeg
decode/reprojection, pipe transfer, tensor preparation and process startup;
because FFmpeg and synchronous Python work can overlap, it is not an exact
CPU-time decomposition.

Privacy-safe metrics are external:

- `outputs/yolox-stream-benchmark/old-ghost-road-t60-68-yaw0-4fps-v3/metrics.json`
- `outputs/yolox-stream-benchmark/old-ghost-road-t60-90-yaw0-4fps-v3/metrics.json`

under `AEGIS_DATA_DIR`. Earlier v1 omitted formal decoder/NMS and v2 did not
time it separately; both remain immutable exploratory records and are not the
reported result.

## Conclusion and follow-up

Adopt one FFmpeg stream plus one model load for sequential detector analysis.
Do not optimize Core ML or projection first: the measured next bottleneck was
the dependency-free Python YOLOX decoder/NMS.

## Vectorized decoder follow-up

A NumPy candidate now vectorizes grid construction, class selection, score
thresholding and box decode while preserving the reference's deterministic
class-aware NMS order. It is optional and does not add NumPy to the normal
dependency-free runtime.

The candidate was compared against the reference on all 32 real Core ML
outputs from the 60–68-second interval. Detection count, class, source index,
score and box values passed the frozen `1e-6` equivalence bound on every
frame. The corrected verification artifact is:

`outputs/yolox-stream-benchmark/old-ghost-road-t60-68-yaw0-4fps-numpy-verify-v2/metrics.json`

under `AEGIS_DATA_DIR`. Its wall time intentionally contains both decoders and
is not a throughput result.

The candidate-only 60–90-second run retains exactly the reference result of 46
person-positive and 15 bicycle-positive frames. It processes 120 frames in
2.172 stream seconds (55.25 fps), including 1.641 seconds Core ML inference,
0.076 seconds vectorized decode/NMS and 0.455 seconds residual work, with
400,506,880 bytes peak RSS. Against the reference v3's 7.433 seconds and 4.528
seconds decode/NMS, total stream throughput improves 3.42× and decode/NMS
improves 59.3× on this interval. The external artifact is:

`outputs/yolox-stream-benchmark/old-ghost-road-t60-90-yaw0-4fps-numpy-v1/metrics.json`

The candidate is suitable for the isolated Core ML analysis environment, but
is not yet the dependency-free reference implementation. Separately run a
180- or 300-second workload with host-visible thermal, swap and power-state
sampling before making a sustained thermal claim.
