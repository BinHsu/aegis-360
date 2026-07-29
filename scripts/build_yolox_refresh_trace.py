#!/usr/bin/env python3
"""Join YOLOX acceptance reports to exact Vision tracker observations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.refresh_trace import (  # noqa: E402
    build_refresh_trace, dumps_refresh_trace,
)
from aegis360.yolox_seed_adapter import yolox_refresh_event  # noqa: E402


def report_arg(value: str) -> tuple[float, Path]:
    raw_timestamp, separator, raw_path = value.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError("report must be TIMESTAMP=JSON")
    try:
        timestamp = float(raw_timestamp)
    except ValueError as error:
        raise argparse.ArgumentTypeError("report timestamp is invalid") from error
    path = Path(raw_path)
    if not math.isfinite(timestamp) or not path.is_file():
        raise argparse.ArgumentTypeError("report timestamp or path is invalid")
    return timestamp, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tracking_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--track-class", choices=("person", "bicycle"), required=True)
    parser.add_argument("--viewport-yaw-degrees", type=float, required=True)
    parser.add_argument("--horizontal-fov-degrees", type=float, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument(
        "--boundary-tolerance-pixels",
        type=float,
        choices=(0.0, 1.0),
        default=0.0,
        help="explicit version-1 edge policy; strict zero remains the default",
    )
    parser.add_argument("--report", type=report_arg, action="append", required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    tracking = json.loads(args.tracking_json.read_text())
    observations = {
        float(row["timestampSeconds"]): row
        for row in tracking["observations"]
    }
    events = []
    for timestamp, path in sorted(args.report):
        report = json.loads(path.read_text())
        if (
            report.get("passed") is not True
            or report.get("threshold_profile") != "acceptance"
            or report.get("preprocessing") != "current"
        ):
            parser.error("YOLOX report is not accepted current-profile evidence")
        observation = observations.get(timestamp)
        if observation is None:
            parser.error(f"no tracker observation at {timestamp}")
        events.append(yolox_refresh_event(
            observation,
            report["candidate_detection_summaries"],
            track_id=tracking["trackId"],
            track_class=args.track_class,
            viewport_yaw=math.radians(args.viewport_yaw_degrees),
            viewport_pitch=0,
            horizontal_fov=math.radians(args.horizontal_fov_degrees),
            aspect_ratio=args.width / args.height,
            viewport_width=args.width,
            viewport_height=args.height,
            boundary_tolerance_pixels=args.boundary_tolerance_pixels,
        ))
    geometry_policy = (
        "one-source-pixel-v1"
        if args.boundary_tolerance_pixels == 1
        else "strict-v1"
    )
    document = build_refresh_trace(
        tuple(events),
        source_id=args.source_id,
        geometry_policy=geometry_policy,
    )
    args.output_json.write_text(dumps_refresh_trace(document), encoding="utf-8")
    print(f"trace={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
