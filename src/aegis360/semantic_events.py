"""Versioned privacy-safe semantic detector events across spherical views."""

from __future__ import annotations

import json
import math
from typing import Iterable, Mapping


SCHEMA_VERSION = "aegis360.semantic-detector-events.v2"
ALLOWED_CLASSES = frozenset(("person", "bicycle"))


def _safe_id(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(token in value for token in ("/", "\\", "://"))
    ):
        raise ValueError(f"{label} must be a path-free nonempty string")
    return value


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be finite")
    return float(value)


def build_semantic_event_artifact(
    *,
    source_id: str,
    model_id: str,
    viewports: Iterable[Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Validate and canonicalize accepted person/bicycle detector evidence."""

    source_id = _safe_id(source_id, "source_id")
    model_id = _safe_id(model_id, "model_id")
    viewport_rows = []
    viewport_ids: set[str] = set()
    for row in viewports:
        if not isinstance(row, Mapping):
            raise ValueError("viewport must be an object")
        viewport_id = _safe_id(row.get("viewport_id"), "viewport_id")
        if viewport_id in viewport_ids:
            raise ValueError("viewport IDs must be unique")
        yaw = _number(row.get("yaw_radians"), "viewport yaw")
        pitch = _number(row.get("pitch_radians"), "viewport pitch")
        h_fov = _number(row.get("horizontal_fov_radians"), "viewport FOV")
        width = row.get("width_pixels")
        height = row.get("height_pixels")
        if not -math.pi <= yaw < math.pi:
            raise ValueError("viewport yaw must be in [-pi, pi)")
        if not -math.pi / 2 <= pitch <= math.pi / 2:
            raise ValueError("viewport pitch must remain between the poles")
        if not 0 < h_fov < math.pi:
            raise ValueError("viewport FOV must be in (0, pi)")
        if (
            not isinstance(width, int) or isinstance(width, bool) or width <= 0
            or not isinstance(height, int) or isinstance(height, bool) or height <= 0
        ):
            raise ValueError("viewport pixel dimensions must be positive integers")
        viewport_ids.add(viewport_id)
        viewport_rows.append({
            "viewport_id": viewport_id,
            "yaw_radians": yaw,
            "pitch_radians": pitch,
            "horizontal_fov_radians": h_fov,
            "width_pixels": width,
            "height_pixels": height,
        })
    if not viewport_rows:
        raise ValueError("at least one viewport is required")

    event_rows = []
    event_keys: set[tuple[float, str]] = set()
    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("event must be an object")
        timestamp = _number(row.get("timestamp_seconds"), "event timestamp")
        viewport_id = _safe_id(row.get("viewport_id"), "event viewport_id")
        if timestamp < 0 or viewport_id not in viewport_ids:
            raise ValueError("event timestamp or viewport reference is invalid")
        key = (timestamp, viewport_id)
        if key in event_keys:
            raise ValueError("timestamp/viewport event pairs must be unique")
        event_keys.add(key)
        detections = row.get("detections")
        if not isinstance(detections, (list, tuple)):
            raise ValueError("event detections must be an array")
        detection_rows = []
        seen_sources: set[int] = set()
        for detection in detections:
            if not isinstance(detection, Mapping):
                raise ValueError("detection must be an object")
            class_name = detection.get("class_name")
            if class_name not in ALLOWED_CLASSES:
                raise ValueError("only accepted person/bicycle detections are allowed")
            score = _number(detection.get("score"), "detection score")
            source_index = detection.get("source_index")
            box = detection.get("box_top_left_normalized")
            if (
                not 0 <= score <= 1
                or not isinstance(source_index, int)
                or isinstance(source_index, bool)
                or source_index < 0
                or source_index in seen_sources
                or not isinstance(box, (list, tuple))
                or len(box) != 4
            ):
                raise ValueError("detection score, source index, or box is invalid")
            seen_sources.add(source_index)
            x, top, width, height = (
                _number(value, "detection box") for value in box
            )
            if (
                x < 0 or top < 0 or width <= 0 or height <= 0
                or x + width > 1 or top + height > 1
            ):
                raise ValueError("detection box must remain inside the viewport")
            detection_rows.append({
                "class_name": class_name,
                "score": score,
                "source_index": source_index,
                "box_top_left_normalized": [x, top, width, height],
                "score_role": "perception_evidence_only",
            })
        event_rows.append({
            "timestamp_seconds": timestamp,
            "viewport_id": viewport_id,
            "detections": sorted(
                detection_rows,
                key=lambda item: (
                    item["class_name"], -item["score"], item["source_index"]
                ),
            ),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "model_id": model_id,
        "coordinate_space": "viewport_top_left_normalized",
        "viewports": sorted(viewport_rows, key=lambda item: item["viewport_id"]),
        "events": sorted(
            event_rows,
            key=lambda item: (item["timestamp_seconds"], item["viewport_id"]),
        ),
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitations": [
            "Detector class and score are perception evidence, not identity or editorial interest.",
            "Cross-viewport duplicates and temporal identity are unresolved in this artifact.",
        ],
    }


def dumps_semantic_event_artifact(document: Mapping[str, object]) -> str:
    return json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
