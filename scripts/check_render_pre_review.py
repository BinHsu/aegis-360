#!/usr/bin/env python3
"""Fail closed before asking a human to compare a rendered slice bundle."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.framing import FramingSafetyConfig  # noqa: E402
from aegis360.pre_review import static_shot_difference  # noqa: E402
from aegis360.shot_render import greedy_trace_to_static_shots  # noqa: E402


def probe(path: Path) -> dict[str, object]:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate",
        "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout).get("streams", [])
    if len(streams) != 1:
        raise ValueError(f"expected one video stream: {path}")
    return streams[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--minimum-change-degrees", type=float, default=8.0)
    parser.add_argument("--minimum-distinct-seconds", type=float, default=2.0)
    args = parser.parse_args()
    trace = json.loads((args.bundle / "trace.json").read_text())
    config = json.loads((args.bundle / "config.json").read_text())
    fixed = args.bundle / "fixed-forward.mp4"
    auto = args.bundle / "auto-directed.mp4"
    media = {"fixed": probe(fixed), "auto": probe(auto)}
    comparable_fields = (
        "codec_name", "profile", "pix_fmt", "width", "height",
        "r_frame_rate", "avg_frame_rate",
    )
    encoding_equal = all(
        media["fixed"].get(field) == media["auto"].get(field)
        for field in comparable_fields
    )
    framing = config["versioned_greedy_config"]["camera"]["framing_safety"]
    safety = FramingSafetyConfig(
        minimum_h_fov=math.radians(
            framing["minimum_horizontal_fov_degrees"]
        ),
        candidate_extent_padding=math.radians(
            framing["candidate_extent_padding_degrees"]
        ),
        max_zoom_in_change=math.radians(
            framing["maximum_zoom_in_change_degrees"]
        ),
    )
    duration = float(config["slice"]["duration_seconds"])
    difference = static_shot_difference(
        greedy_trace_to_static_shots(trace, duration, safety),
        baseline_h_fov=safety.minimum_h_fov,
        minimum_change=math.radians(args.minimum_change_degrees),
        minimum_seconds=args.minimum_distinct_seconds,
    )
    report = {
        "schema_version": "aegis360.pre-review-gate.v1",
        "passed": encoding_equal and bool(difference["passed"]),
        "encoding_comparable": {
            "passed": encoding_equal,
            "fields": list(comparable_fields),
            "streams": media,
            "limitation": (
                "Matching decoded stream properties supplements, but does not "
                "prove, identical encoder options. The renderer contract fixes "
                "both review outputs to libx264 fast CRF 18."
            ),
        },
        "static_shot_difference": difference,
        "human_visual_check_still_required": (
            "Inspect representative decoded frames/contact sheets for blur, "
            "blocking, stitching defects, and meaningful subject differences."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
