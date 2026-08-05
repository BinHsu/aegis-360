"""Build a path-free Vision tracker seed from semantic acquisition evidence."""

from __future__ import annotations

import json
import math
from typing import Mapping

from .semantic_events import SCHEMA_VERSION


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be finite")
    return float(value)


def build_vision_seed_manifest(
    events_document: Mapping[str, object],
    tracklet_report: Mapping[str, object],
    *,
    track_id: str,
    duration_seconds: float,
    sample_fps: float,
) -> dict[str, object]:
    """Choose a deterministic acquisition viewport without retaining a path."""

    if events_document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported semantic event schema")
    if tracklet_report.get("schema_version") != "aegis360.semantic-tracklet-report.v1":
        raise ValueError("unsupported semantic tracklet report schema")
    if (
        not isinstance(track_id, str) or not track_id
        or duration_seconds <= 0 or not math.isfinite(duration_seconds)
        or sample_fps <= 0 or not math.isfinite(sample_fps)
    ):
        raise ValueError("track ID, duration, and sample FPS are required")
    tracklets = tracklet_report.get("tracklets")
    if not isinstance(tracklets, Mapping):
        raise ValueError("tracklets object is required")
    acquisitions = tracklets.get("acquisitions")
    if not isinstance(acquisitions, list):
        raise ValueError("acquisitions must be an array")
    matches = [
        row for row in acquisitions
        if isinstance(row, Mapping) and row.get("track_id") == track_id
    ]
    if len(matches) != 1:
        raise ValueError("track ID must resolve to exactly one acquisition")
    acquisition = matches[0]
    provenance = acquisition.get("acquisition_observation_provenance")
    if not isinstance(provenance, list):
        raise ValueError("acquisition provenance must be an array")
    observations = []
    for value in provenance:
        if not isinstance(value, str) or value.startswith("duplicate-source:"):
            continue
        try:
            row = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("acquisition provenance JSON is invalid") from error
        if not isinstance(row, dict):
            raise ValueError("acquisition provenance must decode to an object")
        box = row.get("box_top_left_normalized")
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError("acquisition box is invalid")
        x, top, width, height = (
            _finite(item, "acquisition box") for item in box
        )
        if (
            x < 0 or top < 0 or width <= 0 or height <= 0
            or x + width > 1 or top + height > 1
            or row.get("class_name") != acquisition.get("class_name")
            or not isinstance(row.get("viewport_id"), str)
            or not isinstance(row.get("source_index"), int)
        ):
            raise ValueError("acquisition provenance contract is invalid")
        observations.append((
            max(width, height), row["viewport_id"], row["source_index"],
            x, top, width, height,
        ))
    if not observations:
        raise ValueError("no usable acquisition observation provenance")
    observations.sort()
    _, viewport_id, source_index, x, top, width, height = observations[0]

    viewport_rows = events_document.get("viewports")
    if not isinstance(viewport_rows, list):
        raise ValueError("viewports must be an array")
    viewports = [
        row for row in viewport_rows
        if isinstance(row, Mapping) and row.get("viewport_id") == viewport_id
    ]
    if len(viewports) != 1:
        raise ValueError("selected viewport must resolve exactly once")
    viewport = viewports[0]
    yaw = _finite(viewport.get("yaw_radians"), "viewport yaw")
    pitch = _finite(viewport.get("pitch_radians"), "viewport pitch")
    h_fov = _finite(viewport.get("horizontal_fov_radians"), "viewport FOV")
    pixel_width = viewport.get("width_pixels")
    pixel_height = viewport.get("height_pixels")
    if (
        not isinstance(pixel_width, int) or isinstance(pixel_width, bool)
        or pixel_width <= 0
        or not isinstance(pixel_height, int) or isinstance(pixel_height, bool)
        or pixel_height <= 0
    ):
        raise ValueError("selected viewport dimensions are invalid")
    source_id = events_document.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source ID is required")
    return {
        "schema_version": "aegis360.semantic-vision-seed.v1",
        "source_id": source_id,
        "track_id": track_id,
        "class_name": acquisition["class_name"],
        "start_seconds": _finite(acquisition.get("acquired_at"), "acquired_at"),
        "duration_seconds": float(duration_seconds),
        "sample_fps": float(sample_fps),
        "viewport": {
            "viewport_id": viewport_id,
            "yaw_degrees": math.degrees(yaw),
            "pitch_degrees": math.degrees(pitch),
            "horizontal_fov_degrees": math.degrees(h_fov),
            "width_pixels": pixel_width,
            "height_pixels": pixel_height,
        },
        "initial_box_vision_bottom_left_normalized": {
            "x": x,
            "y": 1.0 - top - height,
            "width": width,
            "height": height,
        },
        "selection": {
            "policy": "smallest_max_box_dimension_then_viewport_and_source_index",
            "eligible_observation_count": len(observations),
            "selected_source_index": source_index,
            "identity_verified": False,
            "editorial_persistence_allowed": False,
        },
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitation": (
            "The selected semantic observation seeds operational tracking; "
            "it does not establish identity or editorial importance."
        ),
    }
