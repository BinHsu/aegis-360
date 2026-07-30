#!/usr/bin/env python3
"""Benchmark a load-once Core ML detector over one FFmpeg raw-video stream."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import resource
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.yolox_decode import decode_yolox  # noqa: E402
from aegis360.yolox_decode_numpy import decode_yolox_numpy  # noqa: E402


WIDTH = 416
HEIGHT = 416
CHANNELS = 3
FRAME_BYTES = WIDTH * HEIGHT * CHANNELS


def read_exact(stream, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


def ffmpeg_version() -> str:
    result = subprocess.run(
        ["ffmpeg", "-version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("coreml_package", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start-seconds", type=float, required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--sample-fps", type=float, default=4.0)
    parser.add_argument("--viewport-yaw-degrees", type=float, required=True)
    parser.add_argument("--viewport-pitch-degrees", type=float, default=0.0)
    parser.add_argument("--horizontal-fov-degrees", type=float, default=100.0)
    parser.add_argument(
        "--decoder", choices=("reference", "numpy"), default="reference"
    )
    parser.add_argument("--verify-first-frames", type=int, default=0)
    args = parser.parse_args()

    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not args.input_erp.is_file() or not args.coreml_package.exists():
        parser.error("required external input is missing")
    if args.duration_seconds <= 0 or args.sample_fps <= 0:
        parser.error("duration and sample cadence must be positive")
    if args.verify_first_frames < 0:
        parser.error("verification frame count must be nonnegative")
    if args.verify_first_frames and args.decoder != "numpy":
        parser.error("equivalence verification requires the numpy decoder")

    import coremltools as ct
    import numpy as np

    benchmark_started = time.monotonic()
    load_started = time.monotonic()
    model = ct.models.MLModel(str(args.coreml_package))
    model_load_seconds = time.monotonic() - load_started

    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", str(args.start_seconds), "-i", str(args.input_erp),
        "-t", str(args.duration_seconds),
        "-vf", (
            "v360=input=equirect:output=flat:"
            f"w={WIDTH}:h={HEIGHT}:"
            f"yaw={args.viewport_yaw_degrees}:"
            f"pitch={args.viewport_pitch_degrees}:"
            f"h_fov={args.horizontal_fov_degrees}:interp=linear,"
            f"fps={args.sample_fps}"
        ),
        "-an", "-pix_fmt", "bgr24", "-f", "rawvideo", "pipe:1",
    ]
    inference_seconds = 0.0
    postprocess_seconds = 0.0
    equivalence_reference_seconds = 0.0
    equivalence_verified_frames = 0
    decoded_frames = 0
    person_frames = 0
    bicycle_frames = 0
    stream_started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        while True:
            frame = read_exact(process.stdout, FRAME_BYTES)
            if not frame:
                break
            if len(frame) != FRAME_BYTES:
                raise RuntimeError("FFmpeg returned a partial raw-video frame")
            image = np.frombuffer(frame, dtype=np.uint8).reshape(
                HEIGHT, WIDTH, CHANNELS
            )
            tensor = np.ascontiguousarray(
                image.astype(np.float32).transpose(2, 0, 1)[None]
            )
            before = time.monotonic()
            prediction = model.predict({"image": tensor})
            inference_seconds += time.monotonic() - before
            if len(prediction) != 1:
                raise RuntimeError("Core ML output count is invalid")
            raw = np.asarray(next(iter(prediction.values())))[0]

            before = time.monotonic()
            decoder = (
                decode_yolox_numpy if args.decoder == "numpy" else decode_yolox
            )
            detections = decoder(
                raw, confidence_threshold=.25, nms_iou_threshold=.45
            )
            postprocess_seconds += time.monotonic() - before
            if equivalence_verified_frames < args.verify_first_frames:
                before = time.monotonic()
                reference = decode_yolox(
                    raw, confidence_threshold=.25, nms_iou_threshold=.45
                )
                equivalence_reference_seconds += time.monotonic() - before
                if len(reference) != len(detections):
                    raise RuntimeError("decoder equivalence count mismatch")
                for expected, actual in zip(reference, detections):
                    if (
                        expected.class_id != actual.class_id
                        or expected.source_index != actual.source_index
                        or abs(expected.score - actual.score) > 1e-6
                        or any(
                            abs(left - right) > 1e-6
                            for left, right in zip(expected.box, actual.box)
                        )
                    ):
                        raise RuntimeError("decoder equivalence value mismatch")
                equivalence_verified_frames += 1
            person_frames += int(any(row.class_id == 0 for row in detections))
            bicycle_frames += int(any(row.class_id == 1 for row in detections))
            decoded_frames += 1
    finally:
        process.stdout.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait()
    stream_wall_seconds = time.monotonic() - stream_started
    if return_code != 0:
        raise RuntimeError(
            f"FFmpeg raw-video stream failed with code {return_code}: {stderr}"
        )

    elapsed_seconds = time.monotonic() - benchmark_started
    residual_wall_seconds = max(
        0.0,
        stream_wall_seconds
        - inference_seconds
        - postprocess_seconds
        - equivalence_reference_seconds,
    )
    expected_frames = round(args.duration_seconds * args.sample_fps)
    metrics = {
        "schema_version": "aegis360.yolox-coreml-stream-benchmark.v1",
        "source_id": args.source_id,
        "model_id": "yolox_tiny_coco_coreml_float32_v1",
        "configuration": {
            "start_seconds": args.start_seconds,
            "duration_seconds": args.duration_seconds,
            "sample_fps": args.sample_fps,
            "viewport_yaw_degrees": args.viewport_yaw_degrees,
            "viewport_pitch_degrees": args.viewport_pitch_degrees,
            "horizontal_fov_degrees": args.horizontal_fov_degrees,
            "viewport_width": WIDTH,
            "viewport_height": HEIGHT,
            "ffmpeg_process_count": 1,
            "model_load_count": 1,
            "stream_format": "rawvideo_bgr24",
            "decoder": args.decoder,
            "equivalence_verified_frame_count": equivalence_verified_frames,
        },
        "result": {
            "expected_frame_count": expected_frames,
            "decoded_frame_count": decoded_frames,
            "person_positive_frame_count": person_frames,
            "bicycle_positive_frame_count": bicycle_frames,
        },
        "performance": {
            "model_load_seconds": model_load_seconds,
            "coreml_inference_seconds": inference_seconds,
            "yolox_decode_nms_seconds": postprocess_seconds,
            "equivalence_reference_seconds": equivalence_reference_seconds,
            "stream_wall_seconds": stream_wall_seconds,
            "stream_residual_wall_seconds": residual_wall_seconds,
            "elapsed_seconds": elapsed_seconds,
            "achieved_frames_per_second": (
                decoded_frames / stream_wall_seconds
                if stream_wall_seconds else None
            ),
            "maximum_rss_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
            "residual_interpretation": (
                "stream wall minus synchronous inference, selected YOLOX "
                "decode/NMS, and optional equivalence-reference decode; "
                "includes FFmpeg decode/reprojection, pipe transfer, preprocessing, and "
                "process startup, and is not an exact CPU-time decomposition"
            ),
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "ffmpeg": ffmpeg_version(),
        },
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
            "persists_frames": False,
        },
    }
    if decoded_frames != expected_frames:
        raise RuntimeError(
            f"expected {expected_frames} frames, decoded {decoded_frames}"
        )

    args.output_directory.mkdir(parents=True)
    (args.output_directory / "metrics.json").write_text(
        json.dumps(metrics, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "frames": decoded_frames,
        "stream_wall_seconds": stream_wall_seconds,
        "coreml_inference_seconds": inference_seconds,
        "yolox_decode_nms_seconds": postprocess_seconds,
        "achieved_frames_per_second": metrics["performance"][
            "achieved_frames_per_second"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
