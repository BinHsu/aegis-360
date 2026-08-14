"""Convert semantic viewport events into pre-identity spherical evidence."""

from __future__ import annotations

import json
import math
from typing import Mapping

from .geometry import spherical_distance, wrap_yaw
from .perception import (
    AdapterProvenance,
    FrameSample,
    PerceptionResult,
    SignalEvidence,
    SphericalCandidateEvidence,
)
from .semantic_events import ALLOWED_CLASSES, SCHEMA_VERSION
from .spherical_dedup import SphericalDedupConfig, deduplicate_spherical_candidates
from .viewport_rays import viewport_normalized_to_world_ray


ADAPTER = AdapterProvenance(
    "aegis360.semantic-events", "2", "yolox-coreml", "overlapping-viewports"
)
SPHERICAL_SCHEMA_VERSION = "aegis360.semantic-spherical-dedup.v2"


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _angles(ray: tuple[float, float, float]) -> tuple[float, float]:
    return wrap_yaw(math.atan2(ray[0], ray[2])), math.asin(
        max(-1.0, min(1.0, ray[1]))
    )


def semantic_events_to_spherical_results(
    document: Mapping[str, object],
) -> tuple[PerceptionResult, ...]:
    """Project v2 boxes to rays without claiming duplicates or identity."""

    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported semantic event schema")
    source_id = document.get("source_id")
    model_id = document.get("model_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source_id is required")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("model_id is required")
    viewport_rows = document.get("viewports")
    event_rows = document.get("events")
    if not isinstance(viewport_rows, list) or not isinstance(event_rows, list):
        raise ValueError("viewports and events must be arrays")

    viewports: dict[str, dict[str, float | int]] = {}
    for value in viewport_rows:
        row = _mapping(value, "viewport")
        viewport_id = row.get("viewport_id")
        width = row.get("width_pixels")
        height = row.get("height_pixels")
        if (
            not isinstance(viewport_id, str) or not viewport_id
            or viewport_id in viewports
            or not isinstance(width, int) or isinstance(width, bool) or width <= 0
            or not isinstance(height, int) or isinstance(height, bool) or height <= 0
        ):
            raise ValueError("viewport ID or dimensions are invalid")
        yaw = _finite(row.get("yaw_radians"), "viewport yaw")
        pitch = _finite(row.get("pitch_radians"), "viewport pitch")
        h_fov = _finite(row.get("horizontal_fov_radians"), "viewport FOV")
        if not -math.pi <= yaw < math.pi or not -math.pi / 2 <= pitch <= math.pi / 2:
            raise ValueError("viewport pose is invalid")
        if not 0 < h_fov < math.pi:
            raise ValueError("viewport FOV is invalid")
        viewports[viewport_id] = {
            "yaw": yaw, "pitch": pitch, "h_fov": h_fov,
            "width": width, "height": height,
        }
    if not viewports:
        raise ValueError("at least one viewport is required")

    grouped: dict[float, list[SphericalCandidateEvidence]] = {}
    seen_events: set[tuple[float, str]] = set()
    for value in event_rows:
        row = _mapping(value, "event")
        timestamp = _finite(row.get("timestamp_seconds"), "event timestamp")
        viewport_id = row.get("viewport_id")
        detections = row.get("detections")
        if timestamp < 0 or viewport_id not in viewports:
            raise ValueError("event timestamp or viewport is invalid")
        if not isinstance(detections, list):
            raise ValueError("event detections must be an array")
        key = (timestamp, viewport_id)
        if key in seen_events:
            raise ValueError("timestamp/viewport event pairs must be unique")
        seen_events.add(key)
        viewport = viewports[viewport_id]
        aspect = viewport["width"] / viewport["height"]
        output = grouped.setdefault(timestamp, [])
        source_indices: set[int] = set()
        for value_detection in detections:
            detection = _mapping(value_detection, "detection")
            kind = detection.get("class_name")
            score = _finite(detection.get("score"), "detection score")
            source_index = detection.get("source_index")
            box = detection.get("box_top_left_normalized")
            if (
                kind not in ALLOWED_CLASSES or not 0 <= score <= 1
                or not isinstance(source_index, int) or isinstance(source_index, bool)
                or source_index < 0 or source_index in source_indices
                or not isinstance(box, list) or len(box) != 4
            ):
                raise ValueError("detection class, score, source index, or box is invalid")
            source_indices.add(source_index)
            x, top, width, height = (
                _finite(component, "detection box") for component in box
            )
            if (
                x < 0 or top < 0 or width <= 0 or height <= 0
                or x + width > 1 or top + height > 1
            ):
                raise ValueError("detection box must remain in the viewport")
            center_x = x + width / 2
            center_y = top + height / 2
            arguments = (
                viewport["yaw"], viewport["pitch"], viewport["h_fov"], aspect
            )
            center = viewport_normalized_to_world_ray(center_x, center_y, *arguments)
            left = viewport_normalized_to_world_ray(x, center_y, *arguments)
            right = viewport_normalized_to_world_ray(x + width, center_y, *arguments)
            top_ray = viewport_normalized_to_world_ray(center_x, top, *arguments)
            bottom_ray = viewport_normalized_to_world_ray(center_x, top + height, *arguments)
            yaw, pitch = _angles(center)
            left_angles = _angles(left)
            right_angles = _angles(right)
            extent = spherical_distance(left_angles, right_angles)
            vertical_pitches = sorted((_angles(top_ray)[1], _angles(bottom_ray)[1]))
            if not 0 < extent < math.pi:
                raise ValueError("detection spherical extent is invalid")
            candidate_id = f"{viewport_id}:{kind}:{source_index}"
            provenance = json.dumps({
                "adapter": ADAPTER.label,
                "box_top_left_normalized": [x, top, width, height],
                "class_name": kind,
                "model_id": model_id,
                "source_index": source_index,
                "viewport_id": viewport_id,
            }, sort_keys=True, separators=(",", ":"))
            output.append(SphericalCandidateEvidence(
                candidate_id=candidate_id,
                track_id=None,
                yaw=yaw,
                pitch=pitch,
                h_fov=extent,
                candidate_type=kind,
                signals=(SignalEvidence(
                    "detector_confidence", score, score,
                    f"{ADAPTER.label};viewport:{viewport_id}",
                ),),
                observation_provenance=(provenance,),
                pitch_min=vertical_pitches[0],
                pitch_max=vertical_pitches[1],
            ))

    return tuple(
        PerceptionResult(
            FrameSample(
                source_id, timestamp, frame_index,
                max(int(row["width"]) for row in viewports.values()),
                max(int(row["height"]) for row in viewports.values()),
                projection="overlapping_rectilinear_observations",
            ),
            ADAPTER,
            tuple(sorted(candidates, key=lambda item: item.candidate_id)),
        )
        for frame_index, (timestamp, candidates) in enumerate(sorted(grouped.items()))
    )


def build_semantic_spherical_artifact(
    document: Mapping[str, object],
    config: SphericalDedupConfig = SphericalDedupConfig(),
) -> dict[str, object]:
    """Persist same-timestamp geometric clusters with all source provenance."""

    results = semantic_events_to_spherical_results(document)
    rows = []
    raw_count = 0
    merged_count = 0
    duplicate_cluster_count = 0
    largest_cluster_size = 0
    for result in results:
        deduped = deduplicate_spherical_candidates(result, config)
        raw_count += len(result.candidates)
        merged_count += len(deduped.clusters)
        clusters = []
        for cluster in deduped.clusters:
            size = len(cluster.members)
            duplicate_cluster_count += size > 1
            largest_cluster_size = max(largest_cluster_size, size)
            clusters.append({
                "candidate_id": cluster.candidate.candidate_id,
                "class_name": cluster.candidate.candidate_type,
                "yaw_radians": cluster.candidate.yaw,
                "pitch_radians": cluster.candidate.pitch,
                "horizontal_extent_radians": cluster.candidate.h_fov,
                "pitch_min_radians": cluster.candidate.pitch_min,
                "pitch_max_radians": cluster.candidate.pitch_max,
                "member_ids": [member.candidate_id for member in cluster.members],
                "observation_provenance": list(
                    cluster.candidate.observation_provenance
                ),
                "identity_verified": False,
                "editorial_persistence_allowed": False,
            })
        rows.append({
            "timestamp_seconds": result.sample.timestamp,
            "clusters": clusters,
        })
    return {
        "schema_version": SPHERICAL_SCHEMA_VERSION,
        "source_id": document["source_id"],
        "model_id": document["model_id"],
        "dedup_policy": {
            "max_center_distance_radians": config.max_center_distance,
            "extent_overlap_scale": config.extent_overlap_scale,
            "minimum_extent_gate_radians": config.minimum_extent_gate,
            "uses_detector_confidence": False,
        },
        "summary": {
            "timestamp_count": len(rows),
            "raw_observation_count": raw_count,
            "merged_cluster_count": merged_count,
            "duplicate_cluster_count": duplicate_cluster_count,
            "largest_cluster_size": largest_cluster_size,
        },
        "samples": rows,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitations": [
            "Geometric duplicate clusters are not identities or tracks.",
            "Connected-component merging can over-merge crowded nearby subjects.",
            "Detector confidence is retained only inside observation provenance.",
        ],
    }
