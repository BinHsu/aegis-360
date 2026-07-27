#!/usr/bin/env python3
"""Benchmark compile-once Vision registration on generated 2x2 tile media."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
FPS = 25
TILE_WIDTH = 640
TILE_HEIGHT = 360


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def safe_output(command: list[str]) -> str | None:
    try:
        return run(
            command, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def worker(arguments: list[str]) -> int:
    binary = arguments[0]
    inputs = arguments[1:]
    started = time.perf_counter()
    measured = 0
    errors = 0
    for index, input_path in enumerate(inputs):
        output_path = str(Path(input_path).with_suffix(".result.json"))
        run([binary, input_path, output_path])
        result = json.loads(Path(output_path).read_text(encoding="utf-8"))
        measured += result["summary"]["measuredPairCount"]
        errors += result["summary"]["errorPairCount"]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(json.dumps({
        "elapsed_seconds": time.perf_counter() - started,
        "maximum_child_rss_bytes": usage.ru_maxrss,
        "measured_pair_count": measured,
        "error_pair_count": errors,
    }, sort_keys=True))
    return 0


def write_inputs(work: Path, frame_count: int) -> list[Path]:
    duration = frame_count / FPS
    sources = [
        f"testsrc2=s={TILE_WIDTH}x{TILE_HEIGHT}:r={FPS}:d={duration},"
        f"scroll=horizontal={speed}"
        for speed in (0.001, 0.002, 0.003, 0.004)
    ]
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for source in sources:
        command += ["-f", "lavfi", "-i", source]
    command += [
        "-filter_complex",
        "[0:v][1:v][2:v][3:v]"
        "xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]",
        "-map", "[v]", "-frames:v", str(frame_count),
        "-c:v", "ffv1", str(work / "parent.mkv"),
    ]
    run(command)

    positions = ((0, 0), (640, 0), (0, 360), (640, 360))
    input_paths = []
    for index, (x, y) in enumerate(positions):
        tile_dir = work / f"tile-{index}"
        tile_dir.mkdir()
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(work / "parent.mkv"),
            "-vf", f"crop={TILE_WIDTH}:{TILE_HEIGHT}:{x}:{y}",
            "-frames:v", str(frame_count), str(tile_dir / "frame-%06d.png"),
        ])
        frames = [
            {
                "image": str(tile_dir / f"frame-{frame + 1:06d}.png"),
                "timestampSeconds": frame / FPS,
            }
            for frame in range(frame_count)
        ]
        input_path = work / f"tile-{index}.json"
        input_path.write_text(json.dumps({
            "sourceId": f"synthetic-tile-benchmark-{index}",
            "frameWidth": TILE_WIDTH,
            "frameHeight": TILE_HEIGHT,
            "frames": frames,
        }), encoding="utf-8")
        input_paths.append(input_path)
    return input_paths


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        return worker(sys.argv[2:])

    parser = argparse.ArgumentParser()
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--frames", type=int, default=25)
    arguments = parser.parse_args()
    if arguments.output_json.exists():
        raise SystemExit("refusing to overwrite output")
    if not 2 <= arguments.frames <= 250:
        raise SystemExit("--frames must be in [2, 250]")

    with tempfile.TemporaryDirectory(prefix="aegis-vision-tile-benchmark-") as raw:
        work = Path(raw)
        fixture_started = time.perf_counter()
        inputs = write_inputs(work, arguments.frames)
        fixture_seconds = time.perf_counter() - fixture_started

        binary = work / "vision_motion_probe"
        compile_started = time.perf_counter()
        run([
            "swiftc", str(ROOT / "tools/vision_motion_probe.swift"),
            "-o", str(binary),
        ])
        compile_seconds = time.perf_counter() - compile_started

        swap_before = safe_output(["sysctl", "-n", "vm.swapusage"])
        thermal_before = safe_output(["pmset", "-g", "therm"])
        completed = run([
            sys.executable, str(Path(__file__).resolve()), "--worker",
            str(binary), *(str(path) for path in inputs),
        ], text=True, stdout=subprocess.PIPE)
        measurement = json.loads(completed.stdout)
        swap_after = safe_output(["sysctl", "-n", "vm.swapusage"])
        thermal_after = safe_output(["pmset", "-g", "therm"])

    report = {
        "schema_version": "aegis360.vision-tile-benchmark.v1",
        "fixture": {
            "kind": "generated-2x2-independent-scroll",
            "parent_width": TILE_WIDTH * 2,
            "parent_height": TILE_HEIGHT * 2,
            "tile_width": TILE_WIDTH,
            "tile_height": TILE_HEIGHT,
            "tile_count": 4,
            "frame_count_per_tile": arguments.frames,
            "pair_count_total": (arguments.frames - 1) * 4,
            "frames_per_second": FPS,
            "preparation_seconds": fixture_seconds,
        },
        "compile_once_seconds": compile_seconds,
        "measurement": measurement,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "swap_before": swap_before,
            "swap_after": swap_after,
            "thermal_before": thermal_before,
            "thermal_after": thermal_after,
        },
        "privacy": {
            "contains_source_paths": False,
            "contains_pixels": False,
            "contains_identity_data": False,
        },
        "limitations": [
            "Generated scrolling tiles are not spherical camera-motion ground truth.",
            "The measurement loads PNG sequences and runs four tile sequences serially.",
            "It excludes parent-viewport projection and source-video decode.",
        ],
    }
    arguments.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(measurement, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
