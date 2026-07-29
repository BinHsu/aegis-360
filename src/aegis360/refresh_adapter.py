"""Adapt native Vision tracking and Core ML detections to refresh events."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .detector_refresh import RefreshDetection
from .geometry import wrap_yaw
from .refresh_trace import RefreshEvent


def vision_box_center_to_angles(
    box: Mapping[str, object],
    *,
    viewport_yaw: float,
    viewport_pitch: float,
    horizontal_fov: float,
    aspect_ratio: float,
) -> tuple[float, float]:
    values = tuple(float(box[name]) for name in ("x", "y", "width", "height"))
    x, y, width, height = values
    if (
        not all(math.isfinite(value) for value in values)
        or width <= 0 or height <= 0
        or x < 0 or y < 0 or x + width > 1 or y + height > 1
        or aspect_ratio <= 0
        or not 0 < horizontal_fov < math.pi
    ):
        raise ValueError("Vision box or viewport geometry is invalid")
    mid_x = x + width / 2
    mid_y = y + height / 2
    vertical_fov = 2 * math.atan(
        math.tan(horizontal_fov / 2) / aspect_ratio
    )
    yaw_offset = math.atan((2 * mid_x - 1) * math.tan(horizontal_fov / 2))
    pitch_offset = math.atan((2 * mid_y - 1) * math.tan(vertical_fov / 2))
    return (
        wrap_yaw(viewport_yaw + yaw_offset),
        max(-math.pi / 2, min(math.pi / 2, viewport_pitch + pitch_offset)),
    )


def native_refresh_event(
    tracking_observation: Mapping[str, object],
    detection_document: Mapping[str, object],
    *,
    track_id: str,
    track_class: str,
    viewport_yaw: float,
    viewport_pitch: float,
    horizontal_fov: float,
    aspect_ratio: float,
) -> RefreshEvent:
    timestamp = float(tracking_observation["timestampSeconds"])
    track_yaw = tracking_observation.get("yawRadians")
    track_pitch = tracking_observation.get("pitchRadians")
    if (
        tracking_observation.get("state") != "tracked"
        or track_yaw is None or track_pitch is None
    ):
        raise ValueError("refresh requires a tracked observation")
    detections = []
    for index, raw in enumerate(detection_document.get("detections", ())):
        if not isinstance(raw, Mapping):
            raise ValueError("detection must be a mapping")
        labels = raw.get("labels")
        if not isinstance(labels, Sequence) or not labels:
            continue
        top = labels[0]
        if not isinstance(top, Mapping) or not isinstance(
            top.get("identifier"), str
        ):
            raise ValueError("top detection label is invalid")
        if top["identifier"] != track_class:
            continue
        yaw, pitch = vision_box_center_to_angles(
            raw["boundingBox"],
            viewport_yaw=viewport_yaw,
            viewport_pitch=viewport_pitch,
            horizontal_fov=horizontal_fov,
            aspect_ratio=aspect_ratio,
        )
        detections.append(RefreshDetection(
            f"refresh:{timestamp:.3f}:{index}",
            top["identifier"],
            yaw,
            pitch,
        ))
    return RefreshEvent(
        timestamp,
        track_id,
        track_class,
        float(track_yaw),
        float(track_pitch),
        tuple(detections),
    )
