#!/usr/bin/env python3
"""Convert actual Vision homographies into source-to-target SO(3) fits."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.so3 import fit_rotation
from aegis360.viewport_rays import RectilinearViewport, homography_to_world_rays
from aegis360.vision_homography import (
    vision_native_to_source_target_top_left,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vision_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--horizontal-fov-degrees", type=float, required=True)
    arguments = parser.parse_args()

    with arguments.vision_json.open(encoding="utf-8") as handle:
        evidence = json.load(handle)
    viewport = RectilinearViewport(
        width=evidence["frameWidth"],
        height=evidence["frameHeight"],
        yaw=0.0,
        pitch=0.0,
        horizontal_fov=math.radians(arguments.horizontal_fov_degrees),
    )
    observations = []
    for row in evidence["observations"]:
        if row["state"] != "measured":
            continue
        source_to_target = vision_native_to_source_target_top_left(
            row["homographyRowMajor"], viewport.height
        )
        fit = fit_rotation(
            homography_to_world_rays(
                source_to_target, viewport, columns=9, rows=7
            )
        )
        observations.append({
            "frameIndex": row["frameIndex"],
            "timestampSeconds": row["timestampSeconds"],
            "sourceToTargetTopLeftHomographyRowMajor": source_to_target,
            "rotationXyzw": fit.rotation_xyzw,
            "residualRadians": fit.residual_radians,
            "inlierRatio": fit.inlier_ratio,
            "correspondenceCount": fit.correspondence_count,
        })
    output = {
        "schemaVersion": 1,
        "sourceId": evidence["sourceId"],
        "coordinateContract": (
            "source-to-target top-left pixel-center homography; active SO(3) "
            "maps source viewport rays to target viewport rays"
        ),
        "horizontalFovDegrees": arguments.horizontal_fov_degrees,
        "observations": observations,
    }
    arguments.output_json.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output_json.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
