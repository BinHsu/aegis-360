"""Adapt accepted YOLOX top-left boxes to Apple Vision seed coordinates."""

from __future__ import annotations

import math

from .refresh_adapter import native_refresh_event
from .refresh_trace import RefreshEvent


def vision_seed_box(
    detection: dict[str, object],
    *,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    boundary_tolerance_pixels: float = 0,
) -> dict[str, float]:
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
    if (
        not isinstance(boundary_tolerance_pixels, (int, float))
        or not math.isfinite(boundary_tolerance_pixels)
        or boundary_tolerance_pixels < 0
        or boundary_tolerance_pixels > 1
    ):
        raise ValueError("boundary tolerance must be between zero and one pixel")
    if boundary_tolerance_pixels and (
        not isinstance(viewport_width, int)
        or isinstance(viewport_width, bool)
        or viewport_width <= 0
        or not isinstance(viewport_height, int)
        or isinstance(viewport_height, bool)
        or viewport_height <= 0
    ):
        raise ValueError("positive viewport dimensions are required for tolerance")
    x, top, width, height = (float(value) for value in box)
    right = x + width
    lower = top + height
    horizontal_tolerance = (
        boundary_tolerance_pixels / viewport_width
        if boundary_tolerance_pixels else 0
    )
    vertical_tolerance = (
        boundary_tolerance_pixels / viewport_height
        if boundary_tolerance_pixels else 0
    )
    bottom = 1.0 - top - height
    if (
        width <= 0 or height <= 0 or x < 0 or top < 0
        or right > 1 + horizontal_tolerance
        or lower > 1 + vertical_tolerance
    ):
        raise ValueError("YOLOX seed box must fit within the viewport")
    if right > 1:
        width = 1.0 - x
    if lower > 1:
        height = 1.0 - top
        bottom = 0.0
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
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    boundary_tolerance_pixels: float = 0,
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
            "boundingBox": vision_seed_box(
                detection,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                boundary_tolerance_pixels=boundary_tolerance_pixels,
            ),
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
