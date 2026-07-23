"""Convert greedy decisions into static-pose shots for a hard-cut renderer.

This is a reliability fallback for evaluating editorial shot switches.  It
deliberately does not model continuous camera motion between decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Mapping, Sequence

from .geometry import wrap_yaw


@dataclass(frozen=True)
class StaticShot:
    start: float
    end: float
    selected_candidate_id: str
    yaw: float
    pitch: float
    h_fov: float


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _circular_median(values: Sequence[float]) -> float:
    """Return a seam-aware robust center for angles in radians."""

    sine = sum(math.sin(value) for value in values)
    cosine = sum(math.cos(value) for value in values)
    anchor = math.atan2(sine, cosine)
    unwrapped = [
        anchor + math.atan2(math.sin(value - anchor), math.cos(value - anchor))
        for value in values
    ]
    return wrap_yaw(statistics.median(unwrapped))


def greedy_trace_to_static_shots(
    trace: Mapping[str, object], duration: float
) -> tuple[StaticShot, ...]:
    """Group consecutive selected IDs and choose one robust pose per group."""

    if not _finite_number(duration) or duration <= 0:
        raise ValueError("duration must be finite and positive")
    decisions = trace.get("decisions")
    if not isinstance(decisions, (list, tuple)) or not decisions:
        raise ValueError("greedy trace requires at least one decision")

    rows: list[tuple[float, str, float, float, float]] = []
    previous = -math.inf
    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise ValueError("greedy decisions must be mappings")
        timestamp = decision.get("timestamp")
        selected_id = decision.get("selected_candidate_id")
        candidates = decision.get("candidates")
        if (
            not _finite_number(timestamp)
            or float(timestamp) <= previous
            or not isinstance(selected_id, str)
            or not selected_id
            or not isinstance(candidates, (list, tuple))
        ):
            raise ValueError("greedy decision timestamp or selected candidate is invalid")
        selected = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, Mapping)
                and candidate.get("candidate_id") == selected_id
            ),
            None,
        )
        if selected is None:
            raise ValueError("trace selected candidate geometry is missing")
        pose = (
            selected.get("yaw_radians"),
            selected.get("pitch_radians"),
            selected.get("h_fov_radians"),
        )
        if not all(_finite_number(value) for value in pose):
            raise ValueError("static-shot candidate pose must be finite")
        yaw, pitch, h_fov = map(float, pose)
        if pitch < -math.pi / 2 or pitch > math.pi / 2:
            raise ValueError("static-shot pitch is outside [-pi/2, pi/2]")
        if h_fov <= 0 or h_fov >= math.pi:
            raise ValueError("static-shot horizontal FOV must be in (0, pi)")
        rows.append((float(timestamp), selected_id, yaw, pitch, h_fov))
        previous = float(timestamp)

    origin = rows[0][0]
    relative = [(time - origin, candidate, yaw, pitch, fov) for time, candidate, yaw, pitch, fov in rows]
    if relative[-1][0] >= duration:
        raise ValueError("greedy decisions do not fit the requested duration")

    groups: list[list[tuple[float, str, float, float, float]]] = []
    for row in relative:
        if not groups or groups[-1][-1][1] != row[1]:
            groups.append([row])
        else:
            groups[-1].append(row)

    shots: list[StaticShot] = []
    for index, group in enumerate(groups):
        start = group[0][0]
        end = groups[index + 1][0][0] if index + 1 < len(groups) else float(duration)
        shots.append(
            StaticShot(
                start=start,
                end=end,
                selected_candidate_id=group[0][1],
                yaw=_circular_median([row[2] for row in group]),
                pitch=statistics.median(row[3] for row in group),
                h_fov=statistics.median(row[4] for row in group),
            )
        )
    return tuple(shots)
