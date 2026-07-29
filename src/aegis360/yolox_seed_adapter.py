"""Adapt accepted YOLOX top-left boxes to Apple Vision seed coordinates."""

from __future__ import annotations

import math

from .refresh_adapter import native_refresh_event
from .refresh_trace import RefreshEvent


def vision_seed_box(detection: dict[str, object]) -> dict[str, float]:
    if detection.get("class_id") not in (0, 1):
        raise ValueError("only accepted person/bicycle detections can seed")
    score = detection.get("score")
    box = detection.get("box")
    if (
        not isinstance(score, (int, float))
        or not math.isfinite(score)
        or score < .25
        or not isinstance(box, list)
        or len(box) != 4
        or not all(isinstance(value, (int, float)) for value in box)
        or not all(math.isfinite(value) for value in box)
    ):
        raise ValueError("accepted YOLOX detection is invalid")
    x, top, width, height = (float(value) for value in box)
    bottom = 1.0 - top - height
    if (
        width <= 0 or height <= 0 or x < 0 or top < 0
        or x + width > 1 or top + height > 1
    ):
        raise ValueError("YOLOX seed box must fit within the viewport")
    return {"x": x, "y": bottom, "width": width, "height": height}


def yolox_refresh_event(
    observation: dict[str, object],
    detections: list[dict[str, object]],
    *,
    track_id: str,
    track_class: str,
    viewport_yaw: float,
    viewport_pitch: float,
    horizontal_fov: float,
    aspect_ratio: float,
) -> RefreshEvent:
    class_id = {"person": 0, "bicycle": 1}.get(track_class)
    if class_id is None:
        raise ValueError("YOLOX refresh supports person or bicycle tracks")
    native_detections = []
    for detection in detections:
        if detection.get("class_id") != class_id:
            continue
        native_detections.append({
            "labels": [{
                "identifier": track_class,
                "confidence": detection.get("score"),
            }],
            "boundingBox": vision_seed_box(detection),
        })
    return native_refresh_event(
        observation,
        {"detections": native_detections},
        track_id=track_id,
        track_class=track_class,
        viewport_yaw=viewport_yaw,
        viewport_pitch=viewport_pitch,
        horizontal_fov=horizontal_fov,
        aspect_ratio=aspect_ratio,
    )
