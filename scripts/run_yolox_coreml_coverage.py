#!/usr/bin/env python3
"""Run load-once YOLOX Core ML coverage on fixed ERP timestamps/viewports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.yolox_decode import decode_yolox  # noqa: E402


def timestamps(path: Path) -> list[float]:
    values = [
        float(line)
        for raw in path.read_text().splitlines()
        if (line := raw.strip()) and not line.startswith("#")
    ]
    if not values or values != sorted(set(values)):
        raise ValueError("timestamps must be nonempty, unique and increasing")
    return values


def preprocess(image, cv2, np):
    ratio = min(416 / image.shape[0], 416 / image.shape[1])
    resized = cv2.resize(
        image,
        (int(image.shape[1] * ratio), int(image.shape[0] * ratio)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.float32)
    padded = np.full((416, 416, 3), 114.0, dtype=np.float32)
    padded[:resized.shape[0], :resized.shape[1]] = resized
    return np.ascontiguousarray(padded.transpose(2, 0, 1)[None])


def counts(detections):
    return {
        "total": len(detections),
        "person": sum(item.class_id == 0 for item in detections),
        "bicycle": sum(item.class_id == 1 for item in detections),
        "class_ids": [item.class_id for item in detections],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("coreml_package", type=Path)
    parser.add_argument("timestamps_file", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if not all(path.exists() for path in (
        args.input_erp, args.coreml_package, args.timestamps_file
    )):
        parser.error("required external input is missing")

    import coremltools as ct
    import cv2
    import numpy as np

    start = time.monotonic()
    model = ct.models.MLModel(str(args.coreml_package))
    load_seconds = time.monotonic() - start
    rows = []
    with tempfile.TemporaryDirectory(prefix="aegis-yolox-coverage.") as directory:
        frame = Path(directory) / "frame.png"
        inference_seconds = 0.0
        for timestamp in timestamps(args.timestamps_file):
            for yaw in (0, 90, 180, -90):
                subprocess.run([
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-y", "-ss", str(timestamp), "-i", str(args.input_erp),
                    "-frames:v", "1", "-vf",
                    (
                        "v360=input=equirect:output=flat:w=416:h=416:"
                        f"yaw={yaw}:pitch=0:h_fov=100:interp=linear"
                    ),
                    str(frame),
                ], check=True)
                image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
                if image is None:
                    raise RuntimeError("FFmpeg frame decode failed")
                tensor = preprocess(image, cv2, np)
                before = time.monotonic()
                prediction = model.predict({"image": tensor})
                inference_seconds += time.monotonic() - before
                if len(prediction) != 1:
                    raise RuntimeError("Core ML output count is invalid")
                raw = np.asarray(next(iter(prediction.values())))[0]
                acceptance = decode_yolox(
                    raw, confidence_threshold=.25, nms_iou_threshold=.45
                )
                diagnostic = decode_yolox(
                    raw, confidence_threshold=.01, nms_iou_threshold=.65
                )
                rows.append({
                    "timestamp_seconds": timestamp,
                    "yaw_degrees": yaw,
                    "acceptance": counts(acceptance),
                    "official_evaluation_diagnostic": counts(diagnostic),
                })
    elapsed = time.monotonic() - start
    document = {
        "schema_version": "aegis360.yolox-coreml-coverage.v1",
        "source_id": args.source_id,
        "model_id": "yolox_tiny_coco_coreml_float32_v1",
        "preprocessing": "yolox_0.3_current_bgr_0_255",
        "viewport": {
            "yaw_degrees": [0, 90, 180, -90],
            "pitch_degrees": 0,
            "horizontal_fov_degrees": 100,
            "width": 416,
            "height": 416,
        },
        "profiles": {
            "acceptance": {"confidence": .25, "nms_iou": .45},
            "official_evaluation_diagnostic": {
                "confidence": .01, "nms_iou": .65,
                "editorial_acceptance_allowed": False,
            },
        },
        "sample_count": len(rows),
        "samples": rows,
        "summary": {
            "acceptance_person": sum(
                row["acceptance"]["person"] for row in rows
            ),
            "acceptance_bicycle": sum(
                row["acceptance"]["bicycle"] for row in rows
            ),
            "diagnostic_person": sum(
                row["official_evaluation_diagnostic"]["person"] for row in rows
            ),
            "diagnostic_bicycle": sum(
                row["official_evaluation_diagnostic"]["bicycle"] for row in rows
            ),
        },
        "performance": {
            "model_load_seconds": load_seconds,
            "coreml_inference_seconds": inference_seconds,
            "elapsed_seconds": elapsed,
            "maximum_rss_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitations": [
            "Fixed coverage probes are not recall ground truth.",
            "Diagnostic-profile candidates cannot be accepted editorially.",
        ],
    }
    args.output_json.write_text(
        json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(document["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
