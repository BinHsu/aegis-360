# Apple Core ML semantic detector contract — 2026-07-29

Status: Synthetic model/runtime contract passed; natural-image recall untested

## Question

Can the explicitly acquired Apple-hosted YOLOv3 Tiny FP16 model run through
Vision on the reference Mac and emit privacy-safe recognized-object evidence
without adding a Python ML runtime?

## Fixed inputs

- Model ID: `apple_yolov3_tiny_fp16_v2`
- SHA-256:
  `73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda`
- Bytes: 17,769,580
- Canonical record: `model-manifests/manifest.toml`
- Runtime: Swift 6.3.3, Vision and Core ML
- Fixture: generated 416x416 solid-color rectilinear PNG
- Network during the gate: none

## Command

```sh
scripts/run_semantic_detector_contract_gate.sh \
  "$AEGIS_DATA_DIR" /tmp/aegis-semantic-contract.json
```

The runner first verifies the external model manifest and checksum, generates
the bounded fixture, compiles `tools/vision_semantic_detector_gate.swift`, and
runs one `VNCoreMLRequest`. The output must identify the model and checksum,
use `VNRecognizedObjectObservation`, contain no source/model/image path, and
never overwrite an existing output.

## Result

The model compiled and loaded through Core ML. Vision accepted the generated
image and returned a recognized-object result array with zero detections,
which is valid for the featureless fixture. The JSON schema, provenance,
checksum, result type and privacy assertions passed.

Only Command Line Tools are installed; `coremlcompiler` is unavailable.
Runtime `MLModel.compileModel` is the verified host path and requires normal
macOS temporary-directory access.

## Limitations and next gate

This pass proves model/runtime/schema compatibility only. It says nothing
about person or bicycle recall, confidence calibration, projection choice,
identity, tracking continuity, ANE placement, sustained thermals or editorial
value. Next run fixed Old Ghost Road samples over overlapping rectilinear
viewports and record label/box evidence before initializing a tracker.
