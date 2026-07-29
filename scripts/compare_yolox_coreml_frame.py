#!/usr/bin/env python3
"""Compare YOLOX PyTorch and Core ML outputs on one temporary 416px frame."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def document(raw, detections):
    return {
        "tensors": [{
            "name": "raw_head",
            "shape": list(raw.shape),
            "values": raw.reshape(-1).tolist(),
        }],
        "detections": detections,
    }


def top_candidate(raw):
    best = None
    for index, row in enumerate(raw[0]):
        class_id = max(range(80), key=lambda item: (row[5 + item], -item))
        score = float(row[4] * row[5 + class_id])
        candidate = (score, -class_id, -index)
        if best is None or candidate > best[0]:
            best = (candidate, {
                "score": score,
                "class_id": class_id,
                "source_index": index,
            })
    return best[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yolox_source", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("coreml_package", type=Path)
    parser.add_argument("frame", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--preprocessing", choices=("current", "legacy"), default="current"
    )
    parser.add_argument(
        "--threshold-profile",
        choices=("acceptance", "official-evaluation"),
        default="acceptance",
    )
    args = parser.parse_args()
    if args.report.exists():
        parser.error("refusing to overwrite report")
    if not all(path.exists() for path in (
        args.yolox_source, args.checkpoint, args.coreml_package, args.frame
    )):
        parser.error("required external input is missing")
    sys.path.insert(0, str(args.yolox_source))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    import coremltools as ct
    import cv2
    import numpy as np
    import torch
    from aegis360.detector_equivalence import compare_detector_outputs
    from aegis360.yolox_decode import decode_yolox, detection_document
    from yolox.exp import get_exp

    image = cv2.imread(str(args.frame), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("frame must be a decoded color image")
    ratio = min(416 / image.shape[0], 416 / image.shape[1])
    resized = cv2.resize(
        image,
        (int(image.shape[1] * ratio), int(image.shape[0] * ratio)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.float32)
    padded = np.full((416, 416, 3), 114.0, dtype=np.float32)
    padded[:resized.shape[0], :resized.shape[1]] = resized
    if args.preprocessing == "legacy":
        padded = padded[:, :, ::-1] / 255.0
        padded -= np.asarray((.485, .456, .406), dtype=np.float32)
        padded /= np.asarray((.229, .224, .225), dtype=np.float32)
    tensor = np.ascontiguousarray(padded.transpose(2, 0, 1)[None])
    exp = get_exp(
        str(args.yolox_source / "exps/default/yolox_tiny.py"), None
    )
    model = exp.get_model().eval()
    checkpoint = torch.load(
        args.checkpoint, map_location="cpu", weights_only=False
    )
    model.load_state_dict(checkpoint["model"], strict=True)
    model.head.decode_in_inference = False
    with torch.no_grad():
        reference = model(torch.from_numpy(tensor)).cpu().numpy()
    converted = ct.models.MLModel(str(args.coreml_package))
    prediction = converted.predict({"image": tensor})
    if len(prediction) != 1:
        raise RuntimeError("Core ML output count is invalid")
    candidate = np.asarray(next(iter(prediction.values())))
    confidence, nms_iou = (
        (.25, .45) if args.threshold_profile == "acceptance" else (.01, .65)
    )
    reference_detections = detection_document(decode_yolox(
        reference[0],
        confidence_threshold=confidence,
        nms_iou_threshold=nms_iou,
    ))
    candidate_detections = detection_document(decode_yolox(
        candidate[0],
        confidence_threshold=confidence,
        nms_iou_threshold=nms_iou,
    ))
    report = compare_detector_outputs(
        document(reference, reference_detections),
        document(candidate, candidate_detections),
    )
    report.update({
        "source_id": args.source_id,
        "reference_detection_count": len(reference_detections),
        "candidate_detection_count": len(candidate_detections),
        "reference_class_ids": [
            row["class_id"] for row in reference_detections
        ],
        "candidate_class_ids": [
            row["class_id"] for row in candidate_detections
        ],
        "reference_detection_summaries": reference_detections,
        "candidate_detection_summaries": candidate_detections,
        "reference_top_candidate_before_threshold": top_candidate(reference),
        "candidate_top_candidate_before_threshold": top_candidate(candidate),
        "threshold_profile": args.threshold_profile,
        "confidence_threshold": confidence,
        "nms_iou_threshold": nms_iou,
        "preprocessing": args.preprocessing,
    })
    args.report.write_text(
        json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"passed={str(report['passed']).lower()} "
        f"reference_detections={len(reference_detections)} "
        f"candidate_detections={len(candidate_detections)}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
