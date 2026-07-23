#!/usr/bin/env python3
"""Run Apple Vision over a bounded sequence of four-viewpoint samples."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NoReturn


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
VIEWPORTS = (
    ("yaw_0", 0),
    ("yaw_90", 90),
    ("yaw_180", 180),
    ("yaw_minus90", -90),
)
MAX_DURATION_SECONDS = Decimal("300")
MAX_ANALYSIS_FPS = Decimal("10")
MAX_SAMPLES = 3000


def fail(message: str, status: int = 2) -> NoReturn:
    print(f"vision_sequence_gate: {message}", file=sys.stderr)
    raise SystemExit(status)


def decimal_arg(value: str, name: str, *, positive: bool = False) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation:
        fail(f"{name} must be a finite number")
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        fail(f"{name} must be {'positive' if positive else 'non-negative'}")
    return result


def timestamp_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def run_checked(command: list[str], label: str) -> None:
    result = subprocess.run(command, stdout=subprocess.DEVNULL)
    if result.returncode:
        fail(f"{label} failed with status {result.returncode}", 1)


def main() -> None:
    if len(sys.argv) != 7:
        fail(
            "usage: run_vision_sequence_gate.py INPUT_VIDEO OUTPUT_JSON "
            "SOURCE_ID START_SECONDS DURATION_SECONDS ANALYSIS_FPS"
        )

    input_video = Path(sys.argv[1])
    output_json = Path(sys.argv[2])
    source_id = sys.argv[3]
    start = decimal_arg(sys.argv[4], "START_SECONDS")
    duration = decimal_arg(sys.argv[5], "DURATION_SECONDS", positive=True)
    fps = decimal_arg(sys.argv[6], "ANALYSIS_FPS", positive=True)

    if not input_video.is_file():
        fail("input video not found", 1)
    if output_json.exists():
        fail("refusing to overwrite output artifact", 1)
    if not SAFE_ID.fullmatch(source_id):
        fail("SOURCE_ID must be a privacy-safe token")
    if duration > MAX_DURATION_SECONDS:
        fail(f"DURATION_SECONDS exceeds bounded maximum {MAX_DURATION_SECONDS}")
    if fps > MAX_ANALYSIS_FPS:
        fail(f"ANALYSIS_FPS exceeds bounded maximum {MAX_ANALYSIS_FPS}")

    sample_count = int((duration * fps).to_integral_value(rounding="ROUND_CEILING"))
    if sample_count < 1 or sample_count > MAX_SAMPLES:
        fail(f"sequence sample count must be between 1 and {MAX_SAMPLES}")

    repo_dir = Path(__file__).resolve().parent.parent
    swiftc = os.environ.get("AEGIS_SWIFTC", "swiftc")
    ffmpeg = os.environ.get("AEGIS_FFMPEG", "ffmpeg")
    output_json.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aegis-vision-sequence-") as work:
        work_dir = Path(work)
        gate_bin = work_dir / "vision_frame_gate"
        run_checked(
            [swiftc, str(repo_dir / "tools/vision_frame_gate.swift"), "-o", str(gate_bin)],
            "Swift compilation",
        )

        frames: list[dict] = []
        for frame_index in range(sample_count):
            timestamp = start + Decimal(frame_index) / fps
            # Ceil-based sample counts can produce a final point at/after the end.
            if timestamp >= start + duration:
                break
            timestamp_string = timestamp_text(timestamp)
            image_paths: list[Path] = []
            try:
                viewports = []
                for viewport_id, yaw in VIEWPORTS:
                    image_path = work_dir / f"{frame_index:06d}-{viewport_id}.png"
                    run_checked(
                        [
                            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                            "-ss", timestamp_string, "-i", str(input_video),
                            "-frames:v", "1", "-vf",
                            "v360=input=equirect:output=flat:w=640:h=360:"
                            f"yaw={yaw}:pitch=0:h_fov=100:interp=linear",
                            str(image_path),
                        ],
                        "viewport extraction",
                    )
                    image_paths.append(image_path)
                    viewports.append(
                        {
                            "id": viewport_id,
                            "image": str(image_path),
                            "yawDegrees": yaw,
                            "pitchDegrees": 0,
                            "horizontalFovDegrees": 100,
                            "timestampSeconds": float(timestamp),
                        }
                    )

                gate_input = work_dir / "gate-input.json"
                gate_output = work_dir / "gate-output.json"
                gate_input.write_text(
                    json.dumps(
                        {
                            "sourceId": source_id,
                            "frameIndex": frame_index,
                            "viewports": viewports,
                        }
                    ),
                    encoding="utf-8",
                )
                run_checked([str(gate_bin), str(gate_input), str(gate_output)], "Vision analysis")
                result = json.loads(gate_output.read_text(encoding="utf-8"))
                frames.extend(result["frames"])
                gate_input.unlink(missing_ok=True)
                gate_output.unlink(missing_ok=True)
            finally:
                for image_path in image_paths:
                    image_path.unlink(missing_ok=True)

        evidence = {
            "schemaVersion": 1,
            "provenance": {
                "adapterId": "apple-vision-sequence-gate",
                "adapterVersion": "0.1.0",
                "backendId": "Apple Vision (OS-provided requests)",
                "projectionStrategy": "four overlapping rectilinear viewports",
                "visionSwiftCompileCount": 1,
            },
            "sourceId": source_id,
            "sequence": {
                "startSeconds": float(start),
                "durationSeconds": float(duration),
                "analysisFramesPerSecond": float(fps),
                "sampleCount": len(frames) // len(VIEWPORTS),
                "viewportCountPerSample": len(VIEWPORTS),
            },
            "frames": frames,
            "privacy": {
                "containsSourcePath": False,
                "containsPixels": False,
                "temporaryViewportImagesDeletedAfterEachSample": True,
            },
            "limitations": [
                "Four 100-degree equatorial viewports do not cover polar regions.",
                "Candidates are independent Vision observations; this runner does not track or deduplicate them.",
                "Framework availability does not establish CPU/GPU/ANE placement.",
            ],
        }
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=output_json.parent,
                prefix=f".{output_json.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                json.dump(evidence, temporary, indent=2, sort_keys=True)
                temporary.write("\n")
            try:
                os.link(temporary_name, output_json)
            except FileExistsError:
                fail("refusing to overwrite output artifact", 1)
            Path(temporary_name).unlink()
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    print(f"evidence={output_json}")


if __name__ == "__main__":
    main()
