"""Mechanical gates that prevent low-value renders reaching human review."""

from __future__ import annotations

import math
from typing import Iterable

from .shot_render import StaticShot


def static_shot_difference(
    shots: Iterable[StaticShot],
    *,
    baseline_h_fov: float,
    minimum_change: float = math.radians(8.0),
    minimum_seconds: float = 2.0,
    minimum_fraction: float = 0.10,
) -> dict[str, object]:
    """Measure the poses the static renderer actually uses against forward.

    This is only a perceptibility floor. Passing it does not establish that a
    different view contains a better subject or tells a better story.
    """

    rows = tuple(shots)
    if not rows or baseline_h_fov <= 0 or baseline_h_fov >= math.pi:
        raise ValueError("shots and a valid baseline_h_fov are required")
    duration = rows[-1].end
    if duration <= 0:
        raise ValueError("shot duration must be positive")
    details = []
    distinct_seconds = 0.0
    maximum = 0.0
    for shot in rows:
        if shot.end <= shot.start:
            raise ValueError("shot intervals must be positive")
        direction = math.acos(
            max(-1.0, min(1.0, math.cos(shot.pitch) * math.cos(shot.yaw)))
        )
        fov_change = abs(shot.h_fov - baseline_h_fov)
        change = max(direction, fov_change)
        maximum = max(maximum, change)
        distinct = change >= minimum_change
        if distinct:
            distinct_seconds += shot.end - shot.start
        details.append({
            "start_seconds": shot.start,
            "end_seconds": shot.end,
            "selected_candidate_id": shot.selected_candidate_id,
            "yaw_degrees": math.degrees(shot.yaw),
            "pitch_degrees": math.degrees(shot.pitch),
            "horizontal_fov_degrees": math.degrees(shot.h_fov),
            "effective_change_degrees": math.degrees(change),
            "meets_change_floor": distinct,
        })
    required_seconds = max(minimum_seconds, duration * minimum_fraction)
    return {
        "passed": distinct_seconds >= required_seconds,
        "maximum_change_degrees": math.degrees(maximum),
        "distinct_seconds": distinct_seconds,
        "required_distinct_seconds": required_seconds,
        "minimum_change_degrees": math.degrees(minimum_change),
        "shots": details,
        "limitation": (
            "A pass establishes visible pose differentiation only, not "
            "semantic interest, subject continuity, comfort, or quality."
        ),
    }
