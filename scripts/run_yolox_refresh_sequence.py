#!/usr/bin/env python3
"""Run a load-once Core ML detector refresh sequence over a Vision track."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.refresh_lifecycle import (  # noqa: E402
    build_refresh_lifecycle_trace, dumps_refresh_lifecycle_trace,
)
from aegis360.refresh_trace import (  # noqa: E402
    build_refresh_trace, dumps_refresh_trace,
)
from aegis360.tracking_policy import TrackingPolicy  # noqa: E402
from aegis360.yolox_decode import decode_yolox, detection_document  # noqa: E402
from aegis360.yolox_seed_adapter import (  # noqa: E402
    vision_seed_box, yolox_refresh_event,
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("coreml_package", type=Path)
    parser.add_argument("tracking_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--track-class", choices=("person", "bicycle"), required=True)
    parser.add_argument("--viewport-yaw-degrees", type=float, required=True)
    parser.add_argument("--horizontal-fov-degrees", type=float, default=100)
    parser.add_argument(
        "--geometry-policy",
        choices=("strict-v1", "one-source-pixel-v1"),
        default="strict-v1",
    )
    args = parser.parse_args()
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not all(path.exists() for path in (
        args.input_erp, args.coreml_package, args.tracking_json
    )):
        parser.error("required external input is missing")

    import coremltools as ct
    import cv2
    import numpy as np

    tracking = json.loads(args.tracking_json.read_text())
    observations = tracking.get("observations")
    if not isinstance(observations, list) or not observations:
        parser.error("tracking observations are required")
    timestamps = [float(row["timestampSeconds"]) for row in observations]
    if timestamps != sorted(set(timestamps)):
        parser.error("tracking timestamps must be unique and increasing")

    started = time.monotonic()
    model = ct.models.MLModel(str(args.coreml_package))
    load_seconds = time.monotonic() - started
    events = []
    counts = []
    inference_seconds = 0.0
    tolerance = 1.0 if args.geometry_policy == "one-source-pixel-v1" else 0.0
    with tempfile.TemporaryDirectory(prefix="aegis-yolox-refresh.") as directory:
        frame = Path(directory) / "frame.png"
        for observation in observations:
            timestamp = float(observation["timestampSeconds"])
            subprocess.run([
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-y", "-ss", str(timestamp), "-i", str(args.input_erp),
                "-frames:v", "1", "-vf",
                (
                    "v360=input=equirect:output=flat:w=416:h=416:"
                    f"yaw={args.viewport_yaw_degrees}:pitch=0:"
                    f"h_fov={args.horizontal_fov_degrees}:interp=linear"
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
            detections = detection_document(decode_yolox(
                raw, confidence_threshold=.25, nms_iou_threshold=.45
            ))
            target_class_id = 0 if args.track_class == "person" else 1
            valid_detections = []
            rejected_target_geometry = 0
            rejected_overflow_pixels = []
            for detection in detections:
                if detection["class_id"] != target_class_id:
                    valid_detections.append(detection)
                    continue
                try:
                    vision_seed_box(
                        detection,
                        viewport_width=416,
                        viewport_height=416,
                        boundary_tolerance_pixels=tolerance,
                    )
                except ValueError:
                    rejected_target_geometry += 1
                    box = detection.get("box")
                    if isinstance(box, list) and len(box) == 4:
                        x, top, width, height = (
                            float(value) for value in box
                        )
                        rejected_overflow_pixels.append(max(
                            0.0,
                            -x * 416,
                            -top * 416,
                            (x + width - 1) * 416,
                            (top + height - 1) * 416,
                        ))
                else:
                    valid_detections.append(detection)
            events.append(yolox_refresh_event(
                observation,
                valid_detections,
                track_id=tracking["trackId"],
                track_class=args.track_class,
                viewport_yaw=math.radians(args.viewport_yaw_degrees),
                viewport_pitch=0,
                horizontal_fov=math.radians(args.horizontal_fov_degrees),
                aspect_ratio=1,
                viewport_width=416,
                viewport_height=416,
                boundary_tolerance_pixels=tolerance,
            ))
            counts.append({
                "timestamp_seconds": timestamp,
                "decoded_person": sum(row["class_id"] == 0 for row in detections),
                "decoded_bicycle": sum(row["class_id"] == 1 for row in detections),
                "accepted_person": sum(
                    row["class_id"] == 0 for row in valid_detections
                ),
                "accepted_bicycle": sum(
                    row["class_id"] == 1 for row in valid_detections
                ),
                "rejected_target_geometry": rejected_target_geometry,
                "rejected_max_boundary_overflow_pixels": (
                    max(rejected_overflow_pixels)
                    if rejected_overflow_pixels else None
                ),
            })

    refresh = build_refresh_trace(
        tuple(events),
        source_id=args.source_id,
        geometry_policy=args.geometry_policy,
    )
    confidences = {
        float(row["timestampSeconds"]): float(row["confidence"])
        for row in observations
        if row.get("state") == "tracked" and row.get("confidence") is not None
    }
    tracking_policy = TrackingPolicy(
        missing_grace_frames=2, confidence_decay=.75
    )
    first_compatible_index = next((
        index for index, row in enumerate(refresh["events"])
        if row["outcome"] == "compatible_not_identity_verified"
    ), None)
    rejected_before_start = (
        len(refresh["events"])
        if first_compatible_index is None else first_compatible_index
    )
    lifecycle = None
    lifecycle_status = "no_compatible_lifecycle_start"
    lifecycle_consumed_events = 0
    rejected_after_termination = 0
    if first_compatible_index is not None:
        lifecycle_input = dict(refresh)
        lifecycle_input["events"] = refresh["events"][first_compatible_index:]
        lifecycle_status = "all_lifecycle_events_consumed"
        lifecycle_consumed_events = len(lifecycle_input["events"])
        try:
            lifecycle = build_refresh_lifecycle_trace(
                lifecycle_input, confidences, policy=tracking_policy,
            )
        except ValueError as error:
            if str(error) != "terminated tracks cannot be advanced":
                raise
            lifecycle = None
            for event_count in range(1, len(lifecycle_input["events"]) + 1):
                prefix = dict(lifecycle_input)
                prefix["events"] = lifecycle_input["events"][:event_count]
                try:
                    candidate = build_refresh_lifecycle_trace(
                        prefix, confidences, policy=tracking_policy,
                    )
                except ValueError as prefix_error:
                    if str(prefix_error) != "terminated tracks cannot be advanced":
                        raise
                    break
                lifecycle = candidate
                lifecycle_consumed_events = event_count
            if (
                lifecycle is None
                or lifecycle["states"][-1]["phase"] != "terminated"
            ):
                raise RuntimeError("failed to materialize terminated lifecycle")
            lifecycle_status = "events_after_termination_rejected"
            rejected_after_termination = (
                len(lifecycle_input["events"]) - lifecycle_consumed_events
            )
    elapsed_seconds = time.monotonic() - started
    metrics = {
        "schema_version": "aegis360.yolox-refresh-sequence-metrics.v1",
        "source_id": args.source_id,
        "model_id": "yolox_tiny_coco_coreml_float32_v1",
        "geometry_policy": args.geometry_policy,
        "preprocessing": "yolox_0.3_current_bgr_0_255",
        "sample_count": len(counts),
        "samples": counts,
        "lifecycle": {
            "status": lifecycle_status,
            "rejected_before_start_count": rejected_before_start,
            "consumed_event_count": lifecycle_consumed_events,
            "rejected_after_termination_count": rejected_after_termination,
        },
        "performance": {
            "model_load_seconds": load_seconds,
            "coreml_inference_seconds": inference_seconds,
            "elapsed_seconds": elapsed_seconds,
            "maximum_rss_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
    }
    args.output_directory.mkdir(parents=True)
    (args.output_directory / "refresh-trace.json").write_text(
        dumps_refresh_trace(refresh), encoding="utf-8"
    )
    if lifecycle is not None:
        (args.output_directory / "refresh-lifecycle.json").write_text(
            dumps_refresh_lifecycle_trace(lifecycle), encoding="utf-8"
        )
    (args.output_directory / "metrics.json").write_text(
        json.dumps(metrics, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "samples": len(counts),
        "compatible": sum(
            row["outcome"] == "compatible_not_identity_verified"
            for row in refresh["events"]
        ),
        "elapsed_seconds": elapsed_seconds,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
