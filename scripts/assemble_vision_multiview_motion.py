#!/usr/bin/env python3
"""Fuse fixed-viewport Vision registrations into bounded source motion."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.multiview_motion import assemble_source_motion
from aegis360.so3 import fit_rotation
from aegis360.viewport_rays import RectilinearViewport, homography_to_world_rays
from aegis360.vision_homography import vision_native_to_source_target_top_left


def angle(quaternion):
    return 2.0 * math.acos(max(-1.0, min(1.0, abs(quaternion[3]))))


def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("vision_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-id", required=True)
    arguments = parser.parse_args()
    config = load(arguments.config)
    if config.get("schemaVersion") != "aegis360.multiview-motion-config.v1":
        raise SystemExit("unsupported multiview motion config")
    viewport_config = config["viewport"]
    width, height = viewport_config["width"], viewport_config["height"]
    hfov = math.radians(viewport_config["horizontalFovDegrees"])
    declared = []
    evidence = {}
    for item in config["viewports"]:
        viewport_id = item["id"]
        declared.append({
            "id": viewport_id,
            "yawRadians": math.radians(item["yawDegrees"]),
            "pitchRadians": math.radians(item["pitchDegrees"]),
            "horizontalFovRadians": hfov,
        })
        document = load(arguments.vision_directory / f"{viewport_id}.json")
        if document["frameWidth"] != width or document["frameHeight"] != height:
            raise SystemExit(f"{viewport_id}: Vision evidence dimensions disagree with config")
        evidence[viewport_id] = document

    frame_count = len(next(iter(evidence.values()))["observations"])
    if frame_count < 2 or any(len(value["observations"]) != frame_count
                              for value in evidence.values()):
        raise SystemExit("Vision viewport sequences must have equal frame counts >= 2")
    pairs = []
    maximum = math.radians(config["fit"]["maxStepRotationDegrees"])
    minimum_views = config["fit"]["minimumContributingViewports"]
    minimum_confidence = config["fit"]["minimumFitConfidence"]
    minimum_inlier_ratio = config["fit"]["minimumInlierRatio"]
    maximum_residual = math.radians(config["fit"]["maximumFitResidualDegrees"])
    for index in range(1, frame_count):
        correspondences = []
        serialized = []
        previous_time = None
        current_time = None
        contributing = 0
        for viewport_data, item in zip(declared, config["viewports"]):
            observation = evidence[item["id"]]["observations"][index]
            reference = evidence[item["id"]]["observations"][index - 1]
            candidate_previous = reference["timestampSeconds"]
            candidate_current = observation["timestampSeconds"]
            if previous_time is None:
                previous_time = candidate_previous
                current_time = candidate_current
            elif (not math.isclose(previous_time, candidate_previous, abs_tol=1e-9)
                  or not math.isclose(current_time, candidate_current, abs_tol=1e-9)):
                raise SystemExit("Vision viewport timestamps disagree")
            if observation["state"] != "measured":
                continue
            viewport = RectilinearViewport(
                width, height, viewport_data["yawRadians"],
                viewport_data["pitchRadians"], hfov
            )
            converted = vision_native_to_source_target_top_left(
                observation["homographyRowMajor"], height
            )
            # Vision supplies previous(source)->current(target).  The source
            # motion contract wants current rays paired with previous rays.
            rays = homography_to_world_rays(
                converted, viewport,
                columns=config["fit"]["homographyColumns"],
                rows=config["fit"]["homographyRows"],
            )
            contributing += 1
            for previous_ray, current_ray in rays:
                correspondences.append((current_ray, previous_ray))
                serialized.append({
                    "viewportId": item["id"],
                    "previousRay": list(previous_ray),
                    "currentRay": list(current_ray),
                })
        pair = {
            "previousPtsSeconds": previous_time,
            "currentPtsSeconds": current_time,
            "matches": serialized,
        }
        if contributing < minimum_views:
            pair["matches"] = []
            pair["failureReason"] = "insufficient_viewport_coverage"
        else:
            try:
                fit = fit_rotation(correspondences)
                if angle(fit.rotation_xyzw) > maximum:
                    pair["matches"] = []
                    pair["failureReason"] = "rotation_step_exceeds_configured_bound"
                elif fit.confidence < minimum_confidence:
                    pair["matches"] = []
                    pair["failureReason"] = "rotation_fit_confidence_below_bound"
                elif fit.inlier_ratio < minimum_inlier_ratio:
                    pair["matches"] = []
                    pair["failureReason"] = "rotation_fit_inlier_ratio_below_bound"
                elif fit.residual_radians > maximum_residual:
                    pair["matches"] = []
                    pair["failureReason"] = "rotation_fit_residual_exceeds_bound"
            except ValueError:
                pair["matches"] = []
                pair["failureReason"] = "rotation_fit_failed"
        pairs.append(pair)

    bundle = {
        "schemaVersion": "aegis360.multiview-ray-matches.v1",
        "sourceId": arguments.source_id,
        "configId": config["configId"],
        "proxy": config["proxy"],
        "viewports": declared,
        "pairs": pairs,
    }
    output = assemble_source_motion(bundle)
    output["estimator"]["fit_bounds"] = {
        "max_step_rotation_radians": maximum,
        "minimum_contributing_viewports": minimum_views,
        "minimum_fit_confidence": minimum_confidence,
        "minimum_inlier_ratio": minimum_inlier_ratio,
        "maximum_fit_residual_radians": maximum_residual,
        "calibration_basis": config["calibrationBasis"],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
