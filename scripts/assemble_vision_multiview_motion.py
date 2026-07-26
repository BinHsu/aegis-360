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
from aegis360.causal_view_reliability import CausalViewReliability
from aegis360.so3 import fit_rotation, rotate_ray, rotation_distance_radians
from aegis360.view_consensus import select_rotation_consensus
from aegis360.viewport_rays import (
    RectilinearViewport,
    homography_to_world_ray_samples,
)
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
    consensus_config = config.get("viewConsensus")
    causal_config = config.get("causalViewReliability")
    spatial_mask_config = config.get("spatialMask")
    causal_reliability = None
    if causal_config is not None:
        causal_reliability = CausalViewReliability(
            [item["id"] for item in config["viewports"]],
            selected_viewport_count=causal_config[
                "selectedViewportCount"
            ],
            update_alpha=causal_config["updateAlpha"],
        )
    pair_diagnostics = []
    for index in range(1, frame_count):
        causal_selected_ids = (
            causal_reliability.select_for_current_pair()
            if causal_reliability is not None else ()
        )
        causal_scores_before = (
            causal_reliability.scores_radians
            if causal_reliability is not None else {}
        )
        correspondences = []
        serialized = []
        previous_time = None
        current_time = None
        contributing = 0
        per_view = []
        per_view_rotations = {}
        correspondences_by_view = {}
        ray_samples_by_view = {}
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
                per_view.append({
                    "viewport_id": item["id"],
                    "state": "invalid",
                    "failure_reason": "vision_observation_unavailable",
                    "step_rotation_radians": None,
                    "fit_confidence": None,
                    "inlier_ratio": None,
                    "residual_radians": None,
                    "fused_disagreement_radians": None,
                })
                continue
            viewport = RectilinearViewport(
                width, height, viewport_data["yawRadians"],
                viewport_data["pitchRadians"], hfov
            )
            try:
                converted = vision_native_to_source_target_top_left(
                    observation["homographyRowMajor"], height
                )
                # Vision supplies previous(source)->current(target). The
                # source-motion contract wants current rays paired with
                # previous rays.
                ray_samples = homography_to_world_ray_samples(
                    converted, viewport,
                    columns=config["fit"]["homographyColumns"],
                    rows=config["fit"]["homographyRows"],
                )
                rays = [
                    (sample["source_ray"], sample["target_ray"])
                    for sample in ray_samples
                ]
                view_fit = fit_rotation(
                    [(current_ray, previous_ray)
                     for previous_ray, current_ray in rays]
                )
            except ValueError:
                per_view.append({
                    "viewport_id": item["id"],
                    "state": "invalid",
                    "failure_reason": "viewport_rotation_fit_failed",
                    "step_rotation_radians": None,
                    "fit_confidence": None,
                    "inlier_ratio": None,
                    "residual_radians": None,
                    "fused_disagreement_radians": None,
                })
                continue
            contributing += 1
            per_view_rotations[item["id"]] = view_fit.rotation_xyzw
            view_correspondences = [
                (current_ray, previous_ray)
                for previous_ray, current_ray in rays
            ]
            correspondences_by_view[item["id"]] = view_correspondences
            ray_samples_by_view[item["id"]] = ray_samples
            per_view.append({
                "viewport_id": item["id"],
                "state": "measured",
                "failure_reason": None,
                "step_rotation_radians": angle(view_fit.rotation_xyzw),
                "fit_confidence": view_fit.confidence,
                "inlier_ratio": view_fit.inlier_ratio,
                "residual_radians": view_fit.residual_radians,
                "fused_disagreement_radians": None,
            })
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
        diagnostic = {
            "previous_pts_seconds": previous_time,
            "current_pts_seconds": current_time,
            "contributing_viewports": contributing,
            "correspondence_count": len(correspondences),
            "step_rotation_radians": None,
            "fit_confidence": None,
            "inlier_ratio": None,
            "residual_radians": None,
            "state": "measured",
            "failure_reason": None,
            "per_view": per_view,
            "leave_one_view_out": [],
            "view_consensus": None,
            "causal_view_reliability": None,
            "spatial_mask_fit": None,
        }
        if contributing < minimum_views:
            pair["matches"] = []
            pair["failureReason"] = "insufficient_viewport_coverage"
            diagnostic["state"] = "invalid"
            diagnostic["failure_reason"] = pair["failureReason"]
        else:
            try:
                fit = fit_rotation(correspondences)
                diagnostic["step_rotation_radians"] = angle(fit.rotation_xyzw)
                diagnostic["fit_confidence"] = fit.confidence
                diagnostic["inlier_ratio"] = fit.inlier_ratio
                diagnostic["residual_radians"] = fit.residual_radians
                for view in diagnostic["per_view"]:
                    rotation = per_view_rotations.get(view["viewport_id"])
                    if rotation is not None:
                        view["fused_disagreement_radians"] = (
                            rotation_distance_radians(
                                rotation, fit.rotation_xyzw
                            )
                        )
                for omitted_viewport_id in correspondences_by_view:
                    remaining = [
                        match
                        for viewport_id, view_matches
                        in correspondences_by_view.items()
                        if viewport_id != omitted_viewport_id
                        for match in view_matches
                    ]
                    leave_out = {
                        "omitted_viewport_id": omitted_viewport_id,
                        "contributing_viewports": contributing - 1,
                        "step_rotation_radians": None,
                        "fit_confidence": None,
                        "inlier_ratio": None,
                        "residual_radians": None,
                        "state": "measured",
                        "failure_reason": None,
                    }
                    if contributing - 1 < minimum_views:
                        leave_out["state"] = "invalid"
                        leave_out["failure_reason"] = (
                            "insufficient_viewport_coverage"
                        )
                    else:
                        try:
                            leave_fit = fit_rotation(remaining)
                            leave_out["step_rotation_radians"] = angle(
                                leave_fit.rotation_xyzw
                            )
                            leave_out["fit_confidence"] = leave_fit.confidence
                            leave_out["inlier_ratio"] = leave_fit.inlier_ratio
                            leave_out["residual_radians"] = (
                                leave_fit.residual_radians
                            )
                            if leave_out["step_rotation_radians"] > maximum:
                                leave_out["state"] = "invalid"
                                leave_out["failure_reason"] = (
                                    "rotation_step_exceeds_configured_bound"
                                )
                            elif leave_fit.confidence < minimum_confidence:
                                leave_out["state"] = "invalid"
                                leave_out["failure_reason"] = (
                                    "rotation_fit_confidence_below_bound"
                                )
                            elif leave_fit.inlier_ratio < minimum_inlier_ratio:
                                leave_out["state"] = "invalid"
                                leave_out["failure_reason"] = (
                                    "rotation_fit_inlier_ratio_below_bound"
                                )
                            elif leave_fit.residual_radians > maximum_residual:
                                leave_out["state"] = "invalid"
                                leave_out["failure_reason"] = (
                                    "rotation_fit_residual_exceeds_bound"
                                )
                        except ValueError:
                            leave_out["state"] = "invalid"
                            leave_out["failure_reason"] = "rotation_fit_failed"
                    diagnostic["leave_one_view_out"].append(leave_out)
                if consensus_config is not None:
                    selection = select_rotation_consensus(
                        per_view_rotations,
                        maximum_disagreement_radians=math.radians(
                            consensus_config[
                                "maximumMedoidDisagreementDegrees"
                            ]
                        ),
                        minimum_viewports=consensus_config[
                            "minimumSelectedViewports"
                        ],
                    )
                    consensus = {
                        "medoid_viewport_id": selection.medoid_viewport_id,
                        "selected_viewport_ids": list(
                            selection.selected_viewport_ids
                        ),
                        "rejected_viewport_ids": list(
                            selection.rejected_viewport_ids
                        ),
                        "medoid_distances_radians": (
                            selection.medoid_distances_radians
                        ),
                        "step_rotation_radians": None,
                        "fit_confidence": None,
                        "inlier_ratio": None,
                        "residual_radians": None,
                        "state": selection.state,
                        "failure_reason": selection.failure_reason,
                    }
                    if selection.state == "selected":
                        selected_matches = [
                            match
                            for viewport_id in selection.selected_viewport_ids
                            for match in correspondences_by_view[viewport_id]
                        ]
                        try:
                            consensus_fit = fit_rotation(selected_matches)
                            consensus["step_rotation_radians"] = angle(
                                consensus_fit.rotation_xyzw
                            )
                            consensus["fit_confidence"] = (
                                consensus_fit.confidence
                            )
                            consensus["inlier_ratio"] = (
                                consensus_fit.inlier_ratio
                            )
                            consensus["residual_radians"] = (
                                consensus_fit.residual_radians
                            )
                            consensus["state"] = "measured"
                            if consensus["step_rotation_radians"] > maximum:
                                consensus["state"] = "invalid"
                                consensus["failure_reason"] = (
                                    "rotation_step_exceeds_configured_bound"
                                )
                            elif consensus_fit.confidence < minimum_confidence:
                                consensus["state"] = "invalid"
                                consensus["failure_reason"] = (
                                    "rotation_fit_confidence_below_bound"
                                )
                            elif (
                                consensus_fit.inlier_ratio
                                < minimum_inlier_ratio
                            ):
                                consensus["state"] = "invalid"
                                consensus["failure_reason"] = (
                                    "rotation_fit_inlier_ratio_below_bound"
                                )
                            elif (
                                consensus_fit.residual_radians
                                > maximum_residual
                            ):
                                consensus["state"] = "invalid"
                                consensus["failure_reason"] = (
                                    "rotation_fit_residual_exceeds_bound"
                                )
                        except ValueError:
                            consensus["state"] = "invalid"
                            consensus["failure_reason"] = (
                                "rotation_fit_failed"
                            )
                    diagnostic["view_consensus"] = consensus
                if causal_reliability is not None:
                    available_selected = [
                        viewport_id for viewport_id in causal_selected_ids
                        if viewport_id in correspondences_by_view
                    ]
                    causal = {
                        "selected_viewport_ids": available_selected,
                        "rejected_viewport_ids": [
                            viewport_id for viewport_id
                            in sorted(correspondences_by_view)
                            if viewport_id not in available_selected
                        ],
                        "scores_before_radians": causal_scores_before,
                        "rotation_xyzw": None,
                        "spatial_residuals": [],
                        "step_rotation_radians": None,
                        "fit_confidence": None,
                        "inlier_ratio": None,
                        "residual_radians": None,
                        "state": "measured",
                        "failure_reason": None,
                    }
                    if len(available_selected) < minimum_views:
                        causal["state"] = "invalid"
                        causal["failure_reason"] = (
                            "insufficient_viewport_coverage"
                        )
                    else:
                        causal_matches = [
                            match
                            for viewport_id in available_selected
                            for match in correspondences_by_view[viewport_id]
                        ]
                        try:
                            causal_fit = fit_rotation(causal_matches)
                            causal["step_rotation_radians"] = angle(
                                causal_fit.rotation_xyzw
                            )
                            causal["rotation_xyzw"] = list(
                                causal_fit.rotation_xyzw
                            )
                            for viewport_id in available_selected:
                                bands = {"top": [], "middle": [], "bottom": []}
                                for sample in ray_samples_by_view[viewport_id]:
                                    row = sample["row_fraction"]
                                    band = (
                                        "top" if row < 1 / 3
                                        else "middle" if row < 2 / 3
                                        else "bottom"
                                    )
                                    predicted = rotate_ray(
                                        causal_fit.rotation_xyzw,
                                        sample["target_ray"],
                                    )
                                    residual = math.acos(max(
                                        -1.0,
                                        min(1.0, sum(
                                            a * b for a, b in zip(
                                                predicted,
                                                sample["source_ray"],
                                            )
                                        )),
                                    ))
                                    bands[band].append(residual)
                                for band, values in bands.items():
                                    if values:
                                        causal["spatial_residuals"].append({
                                            "viewport_id": viewport_id,
                                            "vertical_band": band,
                                            "sample_count": len(values),
                                            "rms_residual_radians": math.sqrt(
                                                sum(value * value for value in values)
                                                / len(values)
                                            ),
                                        })
                            causal["fit_confidence"] = causal_fit.confidence
                            causal["inlier_ratio"] = causal_fit.inlier_ratio
                            causal["residual_radians"] = (
                                causal_fit.residual_radians
                            )
                            if causal["step_rotation_radians"] > maximum:
                                causal["state"] = "invalid"
                                causal["failure_reason"] = (
                                    "rotation_step_exceeds_configured_bound"
                                )
                            elif causal_fit.confidence < minimum_confidence:
                                causal["state"] = "invalid"
                                causal["failure_reason"] = (
                                    "rotation_fit_confidence_below_bound"
                                )
                            elif causal_fit.inlier_ratio < minimum_inlier_ratio:
                                causal["state"] = "invalid"
                                causal["failure_reason"] = (
                                    "rotation_fit_inlier_ratio_below_bound"
                                )
                            elif causal_fit.residual_radians > maximum_residual:
                                causal["state"] = "invalid"
                                causal["failure_reason"] = (
                                    "rotation_fit_residual_exceeds_bound"
                                )
                        except ValueError:
                            causal["state"] = "invalid"
                            causal["failure_reason"] = "rotation_fit_failed"
                    diagnostic["causal_view_reliability"] = causal
                    if spatial_mask_config is not None:
                        masked_matches = []
                        for viewport_id in available_selected:
                            exclude_bottom = (
                                viewport_id
                                in spatial_mask_config[
                                    "excludeBottomFractionByViewport"
                                ]
                            )
                            for sample in ray_samples_by_view[viewport_id]:
                                if (
                                    exclude_bottom
                                    and sample["row_fraction"]
                                    > 1.0 - spatial_mask_config[
                                        "excludeBottomFraction"
                                    ]
                                ):
                                    continue
                                masked_matches.append((
                                    sample["target_ray"],
                                    sample["source_ray"],
                                ))
                        masked = {
                            "selected_viewport_ids": available_selected,
                            "correspondence_count": len(masked_matches),
                            "rotation_xyzw": None,
                            "step_rotation_radians": None,
                            "fit_confidence": None,
                            "inlier_ratio": None,
                            "residual_radians": None,
                            "state": "measured",
                            "failure_reason": None,
                        }
                        try:
                            masked_fit = fit_rotation(masked_matches)
                            masked["rotation_xyzw"] = list(
                                masked_fit.rotation_xyzw
                            )
                            masked["step_rotation_radians"] = angle(
                                masked_fit.rotation_xyzw
                            )
                            masked["fit_confidence"] = masked_fit.confidence
                            masked["inlier_ratio"] = masked_fit.inlier_ratio
                            masked["residual_radians"] = (
                                masked_fit.residual_radians
                            )
                            if masked["step_rotation_radians"] > maximum:
                                masked["state"] = "invalid"
                                masked["failure_reason"] = (
                                    "rotation_step_exceeds_configured_bound"
                                )
                            elif masked_fit.confidence < minimum_confidence:
                                masked["state"] = "invalid"
                                masked["failure_reason"] = (
                                    "rotation_fit_confidence_below_bound"
                                )
                            elif masked_fit.inlier_ratio < minimum_inlier_ratio:
                                masked["state"] = "invalid"
                                masked["failure_reason"] = (
                                    "rotation_fit_inlier_ratio_below_bound"
                                )
                            elif masked_fit.residual_radians > maximum_residual:
                                masked["state"] = "invalid"
                                masked["failure_reason"] = (
                                    "rotation_fit_residual_exceeds_bound"
                                )
                        except ValueError:
                            masked["state"] = "invalid"
                            masked["failure_reason"] = "rotation_fit_failed"
                        diagnostic["spatial_mask_fit"] = masked
                    if len(per_view_rotations) == len(config["viewports"]):
                        causal_reliability.observe_completed_pair(
                            per_view_rotations
                        )
                if diagnostic["step_rotation_radians"] > maximum:
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
                if "failureReason" in pair:
                    diagnostic["state"] = "invalid"
                    diagnostic["failure_reason"] = pair["failureReason"]
            except ValueError:
                pair["matches"] = []
                pair["failureReason"] = "rotation_fit_failed"
                diagnostic["state"] = "invalid"
                diagnostic["failure_reason"] = pair["failureReason"]
        pairs.append(pair)
        pair_diagnostics.append(diagnostic)

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
        "pair_diagnostics": pair_diagnostics,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
