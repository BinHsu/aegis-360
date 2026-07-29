# Replacement semantic detector shortlist — 2026-07-29

Status: YOLOX-Tiny selected for conversion-feasibility research; no asset acquired

## Trigger

The indexed Apple-hosted YOLOv3 Tiny model produced zero `bicycle` detections
in fixed-five probes across all three public benchmarks. It remains useful for
the native pipeline contract and occasional person seeds, but it has not
passed generic first-person sports coverage.

## Requirements

- COCO `person` and `bicycle` classes.
- Replaceable output behind the existing detector adapter.
- Offline inference on the M4 MacBook Air with 16 GB unified memory.
- Bounded 416×416 viewport inference is preferred for direct comparison.
- Code, weights, training-data provenance and conversion/runtime licenses are
  reviewed independently.
- Conversion must pass numerical equivalence before real-media comparison.
- No model download is authorized by this document.

## Shortlist

| Candidate | Official evidence | POC assessment |
| --- | --- | --- |
| YOLOX-Tiny | Official YOLOX repository is Apache-2.0 and reports 416×416, 5.06M parameters, 6.45 GFLOPs and 32.8 COCO mAP. Official release weights and ONNX export are linked. | Primary conversion-feasibility candidate. It matches the existing viewport size and offers a meaningful accuracy step over Nano without a large model. |
| YOLOX-Nano | Same Apache-2.0 repository; 416×416, 0.91M parameters, 1.08 GFLOPs and 25.8 COCO mAP. | Performance/memory fallback, not the first accuracy probe. Its lower aggregate accuracy may repeat Tiny-detector undercoverage. |
| RT-DETR through PaddleDetection | Official PaddleDetection repository is Apache-2.0 and includes RT-DETR plus deployment tooling. | Deferred. The Paddle→export→Core ML path is longer and less directly documented than the YOLOX PyTorch path, increasing time-to-evidence risk. |
| torchvision COCO detectors | Official torchvision is BSD-3-Clause and Apple documents PyTorch/TorchScript conversion generally. | Deferred. Heavier two-stage models and detector-specific post-processing add iteration cost; general conversion documentation is not proof of an object-detector conversion. |
| Ultralytics models | Official Ultralytics repository uses AGPL-3.0 with a separate enterprise option. | Not the default. Keep isolated unless the owner makes a deliberate licensing decision. |

## Conversion boundary

The YOLOX project officially documents PyTorch checkpoint export to ONNX.
Apple's Core ML Tools documentation supports conversion from PyTorch traced or
exported programs and requires fixed-rank inputs. Neither source establishes
that YOLOX decoding and non-maximum suppression convert correctly.

The next gate must therefore:

1. Record the exact upstream release URL, byte size, SHA-256, upstream commit
   or release, license and local external-storage path before acquisition.
2. Acquire only YOLOX-Tiny after explicit authorization.
3. Produce reference PyTorch outputs and a Core ML artifact from the same
   checkpoint and preprocessing.
4. Compare raw tensor shapes and values before post-processing, then compare
   decoded class IDs, boxes and scores on generated fixtures.
5. Run a bounded 20-viewport compile-once benchmark and record elapsed time,
   maximum RSS and compute-unit configuration.
6. Only after equivalence passes, run the unchanged three-benchmark fixed-five
   coverage probe. Do not tune a confidence threshold after viewing results.

If direct Core ML conversion fails, ONNX Runtime on Apple Silicon is an
allowed temporary comparison backend behind the adapter, but it is not proof
of Core ML feasibility.

## Primary sources

- YOLOX official repository, benchmark table, release weights, ONNX export
  and Apache-2.0 license:
  <https://github.com/Megvii-BaseDetection/YOLOX>
- YOLOX official ONNX Runtime deployment documentation:
  <https://github.com/Megvii-BaseDetection/YOLOX/tree/main/demo/ONNXRuntime>
- PaddleDetection official repository and Apache-2.0 license:
  <https://github.com/PaddlePaddle/PaddleDetection>
- Apple Core ML Tools PyTorch conversion guide:
  <https://apple.github.io/coremltools/docs-guides/source/convert-a-torchvision-model-from-pytorch.html>
- Apple Core ML Tools source/conversion formats:
  <https://apple.github.io/coremltools/docs-guides/source/target-conversion-formats.html>
- torchvision official license:
  <https://github.com/pytorch/vision/blob/main/LICENSE>

## Decision

Research YOLOX-Tiny conversion feasibility first. This is a reversible
experiment choice under ADR 0008, not a permanent backend decision and not
permission to download model assets or dependencies.
