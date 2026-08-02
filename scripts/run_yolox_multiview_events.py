#!/usr/bin/env python3
"""Run one Core ML model over serial viewport streams and persist events."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_events import (  # noqa: E402
    build_semantic_event_artifact, dumps_semantic_event_artifact,
)
from aegis360.yolox_decode_numpy import decode_yolox_numpy  # noqa: E402
from aegis360.yolox_seed_adapter import vision_seed_box  # noqa: E402


CHANNELS = 3
MODEL_ID = "yolox_tiny_coco_coreml_float32_v1"


def _read_exact(stream, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


def _number(value, label, *, positive=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or (value <= 0 if positive else value < 0)
    ):
        raise ValueError(f"{label} is invalid")
    return float(value)


def _load_config(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "aegis360.semantic-multiview-config.v1":
        raise ValueError("unsupported multiview config schema")
    fps = _number(value.get("sample_fps"), "sample_fps", positive=True)
    width = value.get("viewport_width")
    height = value.get("viewport_height")
    tolerance = _number(
        value.get("boundary_tolerance_pixels"), "boundary tolerance"
    )
    if (
        not isinstance(width, int) or isinstance(width, bool) or width <= 0
        or not isinstance(height, int) or isinstance(height, bool) or height <= 0
        or tolerance > 1
    ):
        raise ValueError("viewport dimensions or boundary tolerance are invalid")
    rows = value.get("viewports")
    if not isinstance(rows, list) or not rows:
        raise ValueError("viewports are required")
    ids = set()
    viewports = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("viewport must be an object")
        viewport_id = row.get("viewport_id")
        yaw = row.get("yaw_degrees")
        pitch = row.get("pitch_degrees")
        h_fov = row.get("horizontal_fov_degrees")
        if (
            not isinstance(viewport_id, str) or not viewport_id
            or viewport_id in ids or "/" in viewport_id or "\\" in viewport_id
            or not isinstance(yaw, (int, float)) or not math.isfinite(yaw)
            or not -180 <= yaw < 180
            or not isinstance(pitch, (int, float)) or not math.isfinite(pitch)
            or not -90 <= pitch <= 90
            or not isinstance(h_fov, (int, float)) or not math.isfinite(h_fov)
            or not 0 < h_fov < 180
        ):
            raise ValueError("viewport definition is invalid")
        ids.add(viewport_id)
        viewports.append({
            "viewport_id": viewport_id,
            "yaw_degrees": float(yaw),
            "pitch_degrees": float(pitch),
            "horizontal_fov_degrees": float(h_fov),
        })
    return {
        "sample_fps": fps,
        "viewport_width": width,
        "viewport_height": height,
        "boundary_tolerance_pixels": tolerance,
        "viewports": viewports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("coreml_package", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start-seconds", type=float, required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    args = parser.parse_args()
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not args.input_erp.is_file() or not args.coreml_package.exists() or not args.config.is_file():
        parser.error("required external input is missing")
    if args.start_seconds < 0 or args.duration_seconds <= 0:
        parser.error("start and duration are invalid")

    config = _load_config(args.config)
    width = config["viewport_width"]
    height = config["viewport_height"]
    frame_bytes = width * height * CHANNELS

    import coremltools as ct
    import numpy as np

    started = time.monotonic()
    model_started = time.monotonic()
    model = ct.models.MLModel(str(args.coreml_package))
    model_load_seconds = time.monotonic() - model_started
    events = []
    stream_metrics = []
    total_inference = 0.0
    total_decode = 0.0
    rejected_geometry = 0
    expected_frames = round(args.duration_seconds * config["sample_fps"])

    for viewport in config["viewports"]:
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", str(args.start_seconds), "-i", str(args.input_erp),
            "-t", str(args.duration_seconds),
            "-vf", (
                "v360=input=equirect:output=flat:"
                f"w={width}:h={height}:yaw={viewport['yaw_degrees']}:"
                f"pitch={viewport['pitch_degrees']}:"
                f"h_fov={viewport['horizontal_fov_degrees']}:interp=linear,"
                f"fps={config['sample_fps']}"
            ),
            "-an", "-pix_fmt", "bgr24", "-f", "rawvideo", "pipe:1",
        ]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert process.stdout is not None and process.stderr is not None
        frame_index = 0
        stream_started = time.monotonic()
        try:
            while True:
                frame = _read_exact(process.stdout, frame_bytes)
                if not frame:
                    break
                if len(frame) != frame_bytes:
                    raise RuntimeError("FFmpeg returned a partial raw-video frame")
                image = np.frombuffer(frame, dtype=np.uint8).reshape(
                    height, width, CHANNELS
                )
                tensor = np.ascontiguousarray(
                    image.astype(np.float32).transpose(2, 0, 1)[None]
                )
                before = time.monotonic()
                prediction = model.predict({"image": tensor})
                total_inference += time.monotonic() - before
                if len(prediction) != 1:
                    raise RuntimeError("Core ML output count is invalid")
                raw = np.asarray(next(iter(prediction.values())))[0]
                before = time.monotonic()
                decoded = decode_yolox_numpy(
                    raw, confidence_threshold=.25, nms_iou_threshold=.45,
                )
                total_decode += time.monotonic() - before
                accepted = []
                for detection in decoded:
                    if detection.class_id not in (0, 1):
                        continue
                    detection_document = {
                        "class_id": detection.class_id,
                        "score": detection.score,
                        "box": list(detection.box),
                    }
                    try:
                        vision_box = vision_seed_box(
                            detection_document,
                            viewport_width=width,
                            viewport_height=height,
                            boundary_tolerance_pixels=config[
                                "boundary_tolerance_pixels"
                            ],
                        )
                    except ValueError:
                        rejected_geometry += 1
                        continue
                    accepted.append({
                        "class_name": (
                            "person" if detection.class_id == 0 else "bicycle"
                        ),
                        "score": detection.score,
                        "source_index": detection.source_index,
                        "box_top_left_normalized": [
                            vision_box["x"],
                            1.0 - vision_box["y"] - vision_box["height"],
                            vision_box["width"],
                            vision_box["height"],
                        ],
                    })
                events.append({
                    "timestamp_seconds": (
                        args.start_seconds + frame_index / config["sample_fps"]
                    ),
                    "viewport_id": viewport["viewport_id"],
                    "detections": accepted,
                })
                frame_index += 1
        finally:
            process.stdout.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
        stream_seconds = time.monotonic() - stream_started
        if return_code:
            raise RuntimeError(
                f"FFmpeg viewport stream failed with code {return_code}: {stderr}"
            )
        if frame_index != expected_frames:
            raise RuntimeError(
                f"viewport {viewport['viewport_id']} expected "
                f"{expected_frames} frames, decoded {frame_index}"
            )
        stream_metrics.append({
            "viewport_id": viewport["viewport_id"],
            "decoded_frames": frame_index,
            "stream_wall_seconds": stream_seconds,
        })

    artifact = build_semantic_event_artifact(
        source_id=args.source_id,
        model_id=MODEL_ID,
        viewports=(
            {
                "viewport_id": row["viewport_id"],
                "yaw_radians": math.radians(row["yaw_degrees"]),
                "pitch_radians": math.radians(row["pitch_degrees"]),
                "horizontal_fov_radians": math.radians(
                    row["horizontal_fov_degrees"]
                ),
                "width_pixels": width,
                "height_pixels": height,
            }
            for row in config["viewports"]
        ),
        events=events,
    )
    elapsed = time.monotonic() - started
    metrics = {
        "schema_version": "aegis360.yolox-multiview-events-metrics.v1",
        "source_id": args.source_id,
        "model_id": MODEL_ID,
        "configuration": {
            "start_seconds": args.start_seconds,
            "duration_seconds": args.duration_seconds,
            "sample_fps": config["sample_fps"],
            "viewport_count": len(config["viewports"]),
            "viewport_width": width,
            "viewport_height": height,
            "model_load_count": 1,
            "ffmpeg_streams_serial": True,
        },
        "result": {
            "event_count": len(artifact["events"]),
            "accepted_person_count": sum(
                detection["class_name"] == "person"
                for event in artifact["events"]
                for detection in event["detections"]
            ),
            "accepted_bicycle_count": sum(
                detection["class_name"] == "bicycle"
                for event in artifact["events"]
                for detection in event["detections"]
            ),
            "rejected_geometry_count": rejected_geometry,
            "viewports": stream_metrics,
        },
        "performance": {
            "model_load_seconds": model_load_seconds,
            "coreml_inference_seconds": total_inference,
            "yolox_decode_nms_seconds": total_decode,
            "elapsed_seconds": elapsed,
            "maximum_rss_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "privacy": artifact["privacy"],
    }

    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.",
        dir=args.output_directory.parent,
    ))
    try:
        (staging / "events.json").write_text(
            dumps_semantic_event_artifact(artifact), encoding="utf-8"
        )
        (staging / "metrics.json").write_text(
            json.dumps(metrics, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({
        "events": metrics["result"]["event_count"],
        "person": metrics["result"]["accepted_person_count"],
        "bicycle": metrics["result"]["accepted_bicycle_count"],
        "elapsed_seconds": elapsed,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
