"""Aggregate observed group geometry under an explicit window context."""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics

from .geometry import wrap_yaw
from .group_shot import GroupShot
from .scene_context import SceneContextDecision


@dataclass(frozen=True)
class WindowGroupShot:
    yaw: float
    pitch: float
    horizontal_fov: float
    required_horizontal_fov: float
    observed_sample_count: int
    total_sample_count: int
    observation_ratio: float
    fully_contains_observed_groups: bool
    association_provenance: str = "simultaneous_group_geometry_nonidentity"


def build_window_group_shot(
    context: SceneContextDecision,
    observed_shots: list[GroupShot],
    *,
    total_sample_count: int,
    minimum_observation_ratio: float = 0.5,
    maximum_horizontal_fov: float = math.radians(110),
) -> WindowGroupShot | None:
    """Hold a group pose across bounded misses without merging identities."""

    selected = next(
        (
            candidate for candidate in context.candidates
            if candidate.candidate_id == context.selected_candidate_id
        ),
        None,
    )
    if (
        context.subject_scope != "group"
        or selected is None
        or selected.candidate_type != "group"
        or len(selected.member_candidate_ids) < 2
    ):
        raise ValueError("window group geometry requires group subject scope")
    if not isinstance(total_sample_count, int) or isinstance(total_sample_count, bool) or total_sample_count < 1:
        raise ValueError("total sample count must be a positive integer")
    if len(observed_shots) > total_sample_count:
        raise ValueError("observed shots cannot exceed total samples")
    if (
        not math.isfinite(minimum_observation_ratio)
        or not 0 < minimum_observation_ratio <= 1
        or not math.isfinite(maximum_horizontal_fov)
        or not 0 < maximum_horizontal_fov < math.pi
    ):
        raise ValueError("window group bounds are invalid")
    if not observed_shots:
        return None
    for shot in observed_shots:
        if len(shot.member_ids) < 2:
            raise ValueError("each observation must be a group shot")

    ratio = len(observed_shots) / total_sample_count
    if ratio < minimum_observation_ratio:
        return None
    x = statistics.median(math.sin(shot.yaw) for shot in observed_shots)
    z = statistics.median(math.cos(shot.yaw) for shot in observed_shots)
    if math.hypot(x, z) <= 1e-9:
        return None
    yaw = wrap_yaw(math.atan2(x, z))
    pitch = statistics.median(shot.pitch for shot in observed_shots)
    required = max(
        2 * abs(wrap_yaw(shot.yaw - yaw)) + shot.required_horizontal_fov
        for shot in observed_shots
    )
    horizontal_fov = min(
        maximum_horizontal_fov,
        max(max(shot.horizontal_fov for shot in observed_shots), required),
    )
    return WindowGroupShot(
        yaw=yaw,
        pitch=pitch,
        horizontal_fov=horizontal_fov,
        required_horizontal_fov=required,
        observed_sample_count=len(observed_shots),
        total_sample_count=total_sample_count,
        observation_ratio=ratio,
        fully_contains_observed_groups=required <= maximum_horizontal_fov,
    )
