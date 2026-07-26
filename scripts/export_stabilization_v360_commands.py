#!/usr/bin/env python3
"""Export segment-relative stabilization corrections as v360 sendcmd."""

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.renderer_orientation import (
    quaternion_to_v360_yaw_pitch_roll,
    stabilization_correction,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smoothed_segments", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--segment-index", type=int, default=0)
    parser.add_argument(
        "--composition",
        choices=("canonical", "diagnostic-inverse"),
        default="canonical",
    )
    arguments = parser.parse_args()
    source = json.loads(
        arguments.smoothed_segments.read_text(encoding="utf-8")
    )
    if (
        source.get("schema_version")
        != "aegis360.smoothed-relative-rotation-segments.v1"
    ):
        raise SystemExit("unsupported smoothed-segment schema")
    if arguments.output.exists():
        raise SystemExit("refusing to overwrite output")
    segment = source["segments"][arguments.segment_index]
    anchor = segment["anchor_pts_seconds"]
    lines = []
    for sample in segment["samples"]:
        correction = stabilization_correction(
            sample["relative_orientation_xyzw"],
            sample["smoothed_orientation_xyzw"],
        )
        if arguments.composition == "diagnostic-inverse":
            correction = (
                -correction[0], -correction[1], -correction[2],
                correction[3],
            )
        yaw, pitch, roll = quaternion_to_v360_yaw_pitch_roll(correction)
        timestamp = sample["pts_seconds"] - anchor
        for field, value in (
            ("yaw", yaw), ("pitch", pitch), ("roll", roll)
        ):
            lines.append(
                f"{timestamp:.9f} v360 {field} "
                f"{math.degrees(value):.9f};"
            )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "anchor_pts_seconds": anchor,
        "duration_seconds": (
            segment["samples"][-1]["pts_seconds"] - anchor
        ),
        "sample_count": len(segment["samples"]),
        "command_count": len(lines),
        "composition": arguments.composition,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
