# YOLOX-Tiny conversion-equivalence protocol

Status: Acquired; generated FLOAT32 raw-equivalence gate passed

## Acquisition and generated-gate result

The owner explicitly authorized acquisition. The official release checkpoint
is externally stored at the manifest path:

- byte size: 40,755,013;
- SHA-256:
  `9de513de589ac98bb92d3bca53b5af7b9acfa9b0bacb831f7999d0f7afaee8f0`;
- source tag: `0.1.1rc0`;
- source commit: `e1052df71842031413f6030723c3607b839c80ce`.

Strict checkpoint loading reports zero missing and zero unexpected keys. The
raw, decode-disabled output shape is `(1, 3549, 85)` and all values are finite.

Core ML Tools 9.0 default precision fails the frozen zero gate under both
Torch 2.13.0 and the Core ML Tools-tested Torch 2.7.0: maximum absolute error
1.49157, mean error 0.00423 and top-20 agreement 17/20. This repeatability
isolates default FP16 precision rather than the Torch-version warning.

Explicit FLOAT32 conversion under Torch 2.7.0 passes all five generated
fixtures:

| Fixture | Maximum absolute error | Mean absolute error | Top-20 |
| --- | ---: | ---: | ---: |
| zeros | 0.0001833 | 0.000000236 | 20/20 |
| mid-gray | 0.0000768 | 0.000000315 | 20/20 |
| horizontal gradient | 0.0001125 | 0.000000217 | 20/20 |
| vertical gradient | 0.0000776 | 0.000000187 | 20/20 |
| seeded noise | 0.0000522 | 0.000000168 | 20/20 |

The passing external artifact is
`models/yolox/converted/coremltools-9.0-torch-2.7.0-float32-generated-v2/`
under `AEGIS_DATA_DIR`; it occupies approximately 81 MB including reports and
raw JSON. It is not committed or cleared for redistribution.

## Source and preprocessing correction

The checkpoint release tag `0.1.1rc0` source uses legacy RGB/ImageNet
normalization in its demo. The maintained YOLOX `0.3.0` source defaults to
padded BGR 0–255 and exposes legacy normalization only behind `--legacy`.
Testing established that the current source/preprocessing is the compatible
contract:

- source tag `0.3.0`, commit
  `419778480ab6ec0590e5d3831b3afb3b46ab2aa3`;
- strict checkpoint load passes;
- official dog fixture returns five matching PyTorch/Core ML detections;
- class IDs and ordering match, including COCO bicycle and dog;
- decoded box IoU is at least 0.9999986;
- maximum decoded score difference is 0.00000355.

Reports produced earlier with the `0.1.1rc0` legacy preprocessing are rejected
as coverage evidence. Their raw conversion parity remains informative, but
their semantic outputs must not be compared.

The first valid 360 viewport gate uses Old Ghost Road at 150 seconds, yaw -90.
PyTorch/Core ML raw equivalence passes (maximum error 0.00002474, top-20
20/20), but both retain zero detections at the predeclared confidence 0.25 and
NMS IoU 0.45. The highest pre-threshold candidate is class 14 (`bird`) at
0.23950, not person or bicycle. YOLOX-Tiny therefore has not yet improved the
accepted bicycle coverage on this key viewport.

The official COCO evaluation profile (confidence 0.01, NMS 0.65) was then run
as a diagnostic, not as a replacement acceptance threshold. PyTorch and Core
ML retain the same ten candidates with decoded parity: seven `bird`, two
`clock`, one `person` at score 0.01030, and zero `bicycle`. Agent visual
inspection places the low-score person box plausibly on the central-right
rider in bright yellow shorts. The bird and clock boxes cover riders/bicycles
and are class-confusion false positives. The temporary frame was deleted.

Conclusion: conversion and shared decoding are numerically valid, but this
key 360 viewport provides no bicycle evidence at either profile.

## Three-benchmark Core ML coverage

`scripts/run_yolox_coreml_coverage.py` loads the FLOAT32 package once per
source and processes the same five timestamps and four viewports as the prior
YOLOv3 Tiny probe. Acceptance and official-evaluation diagnostic profiles are
reported separately.

| Source | Acceptance person | Acceptance bicycle | Acceptance target-class viewports | Diagnostic person/bicycle |
| --- | ---: | ---: | ---: | ---: |
| Bellpuig | 7 | 0 | 5/20 | 135 / 0 |
| Old Ghost Road | 1 | 1 | 2/20 | 15 / 2 |
| Skiing | 7 | 0 | 4/20 | 68 / 0 |

The one accepted bicycle occurs at Old Ghost Road 60 seconds, yaw 0, score
0.29753. Its normalized box is approximately `(0.5173, 0.5632, 0.2062,
0.4342)`. Agent visual inspection confirms that it covers the bicycle frame
and front wheel on the hut porch, with some rider/stair overlap. PyTorch/Core
ML box IoU is 0.999999 and score difference is 0.00000335. The temporary frame
was deleted after inspection.

Core ML inference for twenty viewports took 0.35–0.41 seconds per source.
End-to-end elapsed including high-resolution seek/reprojection was 7.84–12.70
seconds. Maximum RSS was 391,888,896–406,142,976 bytes. These are bounded
coverage measurements, not sustained thermal benchmarks.

The diagnostic profile returns many low-score person candidates and cannot be
used as accepted recall evidence. The acceptance result establishes one
plausible bicycle seed where the old model produced zero across its fixed
probe; it does not establish broad bicycle recall or reliable subject
identity.

## Bounded bicycle tracking seed

The v2 Old Ghost Road coverage artifact persists accepted top-left boxes.
`src/aegis360/yolox_seed_adapter.py` accepts only in-frame person/bicycle boxes
at score at least 0.25 and converts them to Apple Vision bottom-left
coordinates.

The confirmed t60/yaw0 bicycle seeds a four-second, 4 fps, 416×416
`VNTrackObjectRequest` run:

- 16/16 tracked, zero lost/error;
- persistence ratio 1.0;
- maximum spherical center step 2.09 degrees;
- confidence 1.0 initially, minimum 0.253 and 0.273 at the final frame.

Three-frame visual inspection shows the box on the same bicycle region at
60.00 and 61.75 seconds. At 63.75 seconds a foreground rider occludes the bike;
the box remains in the bicycle region but includes the rider's yellow shorts
and confidence is low. This is operational bicycle-region continuity, not
verified bicycle identity. The contact sheet was deleted after inspection.

External evidence:
`outputs/vision-tracking-gate/old-ghost-road-t60-yaw0-yolox-bicycle-v1/`.

YOLOX acceptance refreshes at 61, 62 and 63 seconds all return a bicycle
candidate, with scores 0.638, 0.728 and 0.476. The t62 top-left box exceeds
the viewport bottom by approximately 0.00226 normalized units. The strict
adapter rejects this same-class malformed geometry; no clipping or repair is
performed.

The legal t61 and t63 boxes both associate as
`compatible_not_identity_verified`. Their lifecycle states remain active with
tracker confidence 0.936 and 0.432, while identity verification and editorial
persistence remain false. Durable privacy-safe evidence is
`yolox-refresh-trace.json` and `yolox-refresh-lifecycle.json` beside the
external tracking artifact. The excluded t62 result is not silently
represented as a valid refresh.

The upstream YOLOX 0.3.0 `postprocess` implementation converts boxes to corner
coordinates and applies NMS without clipping inference boxes to the image.
The t62 overflow is 0.9408 pixels at 416x416. Under the explicit one-source-
pixel policy in ADR 0009, only the bottom edge is clamped; the center shift is
0.0011308 normalized units, approximately 0.113 degrees in this square
100-degree viewport. A separate v4 trace then contains compatible refreshes
at t61, t62 and t63, while identity and editorial persistence remain false.

External evidence:
`yolox-refresh-trace-one-pixel-v4.json` and
`yolox-refresh-lifecycle-one-pixel-v4.json` beside the tracking artifact.
Both explicitly carry `geometry_policy: one-source-pixel-v1`.

## Objective

Determine whether the official YOLOX-Tiny COCO checkpoint can become a
replaceable Core ML detector on the reference M4/16 GB Mac without changing
the downstream spherical detector contract.

## Preconditions

- Explicit authorization to acquire the exact proposed asset.
- Candidate record in `model-manifests/candidates.toml`.
- Record actual byte size and SHA-256 before moving the entry to the installed
  model manifest.
- Isolated conversion environment; do not add PyTorch, YOLOX, ONNX or
  Core ML Tools to the normal runtime.
- Preserve the upstream checkpoint and every derived artifact outside Git.

## Frozen inputs

Use generated RGB fixtures at 416×416:

1. all zeros;
2. constant mid-gray;
3. deterministic horizontal and vertical gradients;
4. deterministic seeded noise.

Then use the already licensed fixed-five benchmark viewports only after tensor
equivalence passes. Extracted images remain temporary and are deleted after
aggregation.

## Equivalence gates

Compare the upstream PyTorch reference with the converted Core ML model before
NMS:

- identical output tensor count and shapes;
- all values finite;
- maximum absolute error ≤ 0.02;
- mean absolute error ≤ 0.005;
- top-20 flattened score indices agree for at least 19/20 entries.

Compare decoded outputs using one frozen confidence threshold and NMS IoU
threshold declared before real images:

- identical COCO class IDs for matched outputs;
- at least 0.95 box IoU for every matched retained box;
- absolute score difference ≤ 0.03;
- no unmatched retained output on generated fixtures.

A failure is a conversion failure. Do not relax thresholds after inspecting
benchmark footage.

The vendor-neutral comparison boundary is implemented in
`src/aegis360/detector_equivalence.py` with CLI
`scripts/compare_detector_equivalence.py`. Reference and candidate backends
must export ordered raw tensors plus decoded detections to its JSON contract.
The checker fails closed on shape, finite-value, class, score or box errors and
emits a privacy-safe report. It does not load a model or perform NMS itself.

## Runtime gate

Run twenty viewports in one compile/load process and record:

- macOS and hardware identity;
- Python, PyTorch, YOLOX and Core ML Tools versions used for conversion;
- checkpoint and Core ML artifact SHA-256 and byte size;
- Core ML compute-unit configuration;
- cold compile/load time and sustained twenty-viewport elapsed time;
- maximum RSS, swap delta and thermal/performance warnings.

The bounded gate fails if maximum RSS reaches 10 GB, swap grows, any output is
non-finite, or the process cannot complete all twenty samples.

## Coverage comparison

Only after equivalence passes, run the same timestamp files, viewports,
projection, resolution and untuned thresholds as the current fixed-five
coverage probe. Record person/bicycle candidate counts and visually audit
every claimed bicycle box. This remains a coverage probe, not recall ground
truth.

## Stop conditions

- Do not acquire or convert another model merely because YOLOX-Tiny fails.
- Do not lower confidence after viewing outputs.
- Do not promote class/geometry compatibility to identity.
- Do not commit checkpoints, converted packages, extracted frames or absolute
  paths.
