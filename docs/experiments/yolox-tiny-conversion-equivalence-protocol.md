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
