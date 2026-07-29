#!/usr/bin/env python3
"""Combine native tracking and detector refresh JSON into a safe trace."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.refresh_adapter import native_refresh_event  # noqa: E402
from aegis360.refresh_trace import (  # noqa: E402
    build_refresh_trace, dumps_refresh_trace,
)


def detection_arg(value: str) -> tuple[float, Path]:
    try:
        raw_timestamp, raw_path = value.split("=", 1)
        timestamp = float(raw_timestamp)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "detection must be TIMESTAMP=JSON"
        ) from error
    path = Path(raw_path)
    if not math.isfinite(timestamp) or not path.is_file():
        raise argparse.ArgumentTypeError("invalid detection timestamp or path")
    return timestamp, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tracking_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--track-class", required=True)
    parser.add_argument("--viewport-yaw-degrees", type=float, required=True)
    parser.add_argument("--viewport-pitch-degrees", type=float, default=0)
    parser.add_argument("--horizontal-fov-degrees", type=float, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument(
        "--detection", type=detection_arg, action="append", required=True
    )
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    tracking = json.loads(args.tracking_json.read_text())
    observations = {
        float(row["timestampSeconds"]): row
        for row in tracking["observations"]
    }
    events = []
    for timestamp, path in sorted(args.detection):
        observation = observations.get(timestamp)
        if observation is None:
            parser.error(f"no tracking observation at {timestamp}")
        events.append(native_refresh_event(
            observation,
            json.loads(path.read_text()),
            track_id=tracking["trackId"],
            track_class=args.track_class,
            viewport_yaw=math.radians(args.viewport_yaw_degrees),
            viewport_pitch=math.radians(args.viewport_pitch_degrees),
            horizontal_fov=math.radians(args.horizontal_fov_degrees),
            aspect_ratio=args.width / args.height,
        ))
    document = build_refresh_trace(tuple(events), source_id=args.source_id)
    args.output_json.write_text(dumps_refresh_trace(document), encoding="utf-8")
    print(f"trace={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
