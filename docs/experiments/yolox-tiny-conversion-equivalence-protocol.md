# YOLOX-Tiny conversion-equivalence protocol

Status: Predeclared protocol; candidate not acquired

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
