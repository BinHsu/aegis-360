#!/usr/bin/env python3
"""Smooth independently anchored relative-orientation segments."""

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.quaternion_smoothing import smooth_quaternion_path
from aegis360.so3 import rotation_distance_radians


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return None
    return {
        "median": statistics.median(ordered),
        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
        "maximum": ordered[-1],
    }


def dynamics(samples, field):
    speeds = []
    for first, second in zip(samples, samples[1:]):
        delta = second["pts_seconds"] - first["pts_seconds"]
        speeds.append(
            rotation_distance_radians(first[field], second[field]) / delta
        )
    accelerations = [
        abs(second - first) / (
            samples[index + 2]["pts_seconds"]
            - samples[index + 1]["pts_seconds"]
        )
        for index, (first, second) in enumerate(zip(speeds, speeds[1:]))
    ]
    jerks = [
        abs(second - first) / (
            samples[index + 3]["pts_seconds"]
            - samples[index + 2]["pts_seconds"]
        )
        for index, (first, second) in enumerate(
            zip(accelerations, accelerations[1:])
        )
    ]
    return {
        "angular_speed_radians_per_second": distribution(speeds),
        "scalar_acceleration_proxy_radians_per_second2": distribution(
            accelerations
        ),
        "scalar_jerk_proxy_radians_per_second3": distribution(jerks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relative_segments", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    source = json.loads(
        arguments.relative_segments.read_text(encoding="utf-8")
    )
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    if source.get("schema_version") != "aegis360.relative-rotation-segments.v1":
        raise SystemExit("unsupported relative-segment schema")
    if (
        config.get("schemaVersion")
        != "aegis360.quaternion-smoothing-config.v1"
    ):
        raise SystemExit("unsupported smoothing config schema")
    if arguments.output.exists():
        raise SystemExit("refusing to overwrite output")

    segments = []
    for source_segment in source["segments"]:
        timestamps = [
            sample["pts_seconds"] for sample in source_segment["samples"]
        ]
        raw = [
            sample["relative_orientation_xyzw"]
            for sample in source_segment["samples"]
        ]
        smoothed = smooth_quaternion_path(
            timestamps, raw,
            radius_seconds=config["radiusSeconds"],
            maximum_correction_radians=math.radians(
                config["maximumCorrectionDegrees"]
            ),
        )
        samples = []
        for source_sample, smooth in zip(
            source_segment["samples"], smoothed
        ):
            samples.append({
                **source_sample,
                "smoothed_orientation_xyzw": list(smooth),
                "correction_angle_radians": rotation_distance_radians(
                    source_sample["relative_orientation_xyzw"], smooth
                ),
            })
        segments.append({
            **{key: value for key, value in source_segment.items()
               if key != "samples"},
            "samples": samples,
            "raw_dynamics": dynamics(
                samples, "relative_orientation_xyzw"
            ),
            "smoothed_dynamics": dynamics(
                samples, "smoothed_orientation_xyzw"
            ),
            "correction_angle_radians": distribution([
                sample["correction_angle_radians"] for sample in samples
            ]),
        })

    document = {
        "schema_version": "aegis360.smoothed-relative-rotation-segments.v1",
        "source_id": source["source_id"],
        "source_config_id": source["source_config_id"],
        "gap_policy_config_id": source["gap_policy_config_id"],
        "smoothing_config_id": config["configId"],
        "coordinate_convention": source["coordinate_convention"],
        "segments": segments,
        "privacy": source["privacy"],
        "limitations": [
            "Smoothed orientations remain relative to each segment anchor.",
            "No relationship is claimed across invalid gaps.",
            "The path has not passed renderer or viewer-comfort validation.",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "segment_count": len(segments),
        "sample_count": sum(len(item["samples"]) for item in segments),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
