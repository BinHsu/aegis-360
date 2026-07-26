#!/usr/bin/env python3
"""Run a bounded, analysis-only multiview source-motion probe on local ERP media."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_command_output(command: list[str]) -> str | None:
    try:
        return subprocess.run(
            command, check=True, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    arguments = parser.parse_args()

    if not arguments.input_erp.is_file():
        parser.error("input ERP does not exist")
    if arguments.output_dir.exists():
        parser.error("refusing to overwrite output directory")
    if arguments.start < 0 or arguments.duration <= 0:
        parser.error("start must be nonnegative and duration must be positive")
    config = load(arguments.config)
    viewport = config["viewport"]
    fps = config["proxy"]["sampleFps"]
    expected_frames = math.ceil(arguments.duration * fps)
    if expected_frames < 2:
        parser.error("configured interval must contain at least two samples")

    started = time.monotonic()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with tempfile.TemporaryDirectory(prefix="aegis-real-multiview-") as temporary:
        private = Path(temporary)
        binary = private / "vision_motion_probe"
        run([
            "xcrun", "swiftc", str(ROOT / "tools/vision_motion_probe.swift"),
            "-o", str(binary),
        ])
        vision_dir = private / "vision"
        vision_dir.mkdir()
        viewport_summaries = {}
        for view in config["viewports"]:
            frames_dir = private / f"frames-{view['id']}"
            frames_dir.mkdir()
            filter_graph = (
                f"fps={fps},"
                f"v360=input=equirect:output=flat:w={viewport['width']}:"
                f"h={viewport['height']}:yaw={view['yawDegrees']}:"
                f"pitch={view['pitchDegrees']}:"
                f"h_fov={viewport['horizontalFovDegrees']}:interp=linear"
            )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(arguments.start), "-t", str(arguments.duration),
                "-i", str(arguments.input_erp), "-an", "-vf", filter_graph,
                "-start_number", "0", str(frames_dir / "%06d.png"),
            ])
            frames = sorted(frames_dir.glob("*.png"))
            if len(frames) != expected_frames:
                raise RuntimeError(
                    f"{view['id']}: expected {expected_frames} frames, got {len(frames)}"
                )
            probe_input = {
                "sourceId": f"{arguments.source_id}-{view['id']}",
                "frameWidth": viewport["width"],
                "frameHeight": viewport["height"],
                "frames": [
                    {
                        "image": str(path),
                        "timestampSeconds": index / fps,
                    }
                    for index, path in enumerate(frames)
                ],
            }
            input_json = private / f"{view['id']}-input.json"
            evidence_json = vision_dir / f"{view['id']}.json"
            input_json.write_text(json.dumps(probe_input), encoding="utf-8")
            run([str(binary), str(input_json), str(evidence_json)])
            evidence = load(evidence_json)
            viewport_summaries[view["id"]] = evidence["summary"]

        arguments.output_dir.mkdir(parents=True)
        source_motion = arguments.output_dir / "source-motion.json"
        run([
            sys.executable,
            str(ROOT / "scripts/assemble_vision_multiview_motion.py"),
            str(arguments.config), str(vision_dir), str(source_motion),
            "--source-id", arguments.source_id,
        ])

    elapsed = time.monotonic() - started
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    motion = load(source_motion)
    diagnostics = motion["estimator"]["fit_bounds"]["pair_diagnostics"]
    measured = sum(row["state"] == "measured" for row in diagnostics)
    reasons: dict[str, int] = {}
    for row in diagnostics:
        if row["failure_reason"]:
            reasons[row["failure_reason"]] = reasons.get(row["failure_reason"], 0) + 1
    ffmpeg_version = (safe_command_output(["ffmpeg", "-version"]) or "").splitlines()
    swap = safe_command_output(["sysctl", "-n", "vm.swapusage"])
    report = {
        "schema_version": "aegis360.real-multiview-motion-report.v1",
        "source_id": arguments.source_id,
        "config_id": config["configId"],
        "interval": {
            "start_seconds": arguments.start,
            "duration_seconds": arguments.duration,
            "sample_fps": fps,
            "sample_count": len(motion["samples"]),
        },
        "outcome": {
            "pair_count": len(diagnostics),
            "measured_pair_count": measured,
            "invalid_pair_count": len(diagnostics) - measured,
            "measured_pair_fraction": measured / len(diagnostics),
            "failure_reasons": reasons,
        },
        "viewport_summaries": viewport_summaries,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "ffmpeg_version": ffmpeg_version[0] if ffmpeg_version else "unknown",
            "elapsed_seconds": elapsed,
            "child_max_rss_bytes": max(
                usage_before.ru_maxrss, usage_after.ru_maxrss
            ),
            "swapusage": swap or "unavailable",
        },
        "artifacts": {
            "source_motion": "source-motion.json",
            "contains_source_path": False,
            "contains_frames": False,
        },
        "limitations": [
            "Analysis-only evidence; no stabilized or viewer-review video was rendered.",
            "Vision homographies may include parallax, moving subjects, blur, and stitching artifacts.",
            "Measured-pair fraction is not a viewer-comfort metric.",
        ],
    }
    (arguments.output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["outcome"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
