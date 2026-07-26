"""Deterministic view-level rotation consensus."""

from dataclasses import dataclass

from .so3 import Quaternion, rotation_distance_radians


@dataclass(frozen=True)
class ViewConsensus:
    medoid_viewport_id: str
    selected_viewport_ids: tuple[str, ...]
    rejected_viewport_ids: tuple[str, ...]
    medoid_distances_radians: dict[str, float]
    state: str
    failure_reason: str | None


def select_rotation_consensus(
    rotations: dict[str, Quaternion],
    *,
    maximum_disagreement_radians: float,
    minimum_viewports: int,
) -> ViewConsensus:
    """Select views near the rotation medoid without inspecting fit outcome."""

    if maximum_disagreement_radians < 0.0:
        raise ValueError("maximum disagreement must be nonnegative")
    if minimum_viewports < 1:
        raise ValueError("minimum viewports must be positive")
    if not rotations:
        raise ValueError("at least one rotation is required")

    viewport_ids = sorted(rotations)
    medoid = min(
        viewport_ids,
        key=lambda candidate: (
            sum(
                rotation_distance_radians(
                    rotations[candidate], rotations[other]
                )
                for other in viewport_ids
            ),
            candidate,
        ),
    )
    distances = {
        viewport_id: rotation_distance_radians(
            rotations[medoid], rotations[viewport_id]
        )
        for viewport_id in viewport_ids
    }
    selected = tuple(
        viewport_id for viewport_id in viewport_ids
        if distances[viewport_id] <= maximum_disagreement_radians
    )
    rejected = tuple(
        viewport_id for viewport_id in viewport_ids
        if viewport_id not in selected
    )
    enough = len(selected) >= minimum_viewports
    return ViewConsensus(
        medoid_viewport_id=medoid,
        selected_viewport_ids=selected,
        rejected_viewport_ids=rejected,
        medoid_distances_radians=distances,
        state="selected" if enough else "invalid",
        failure_reason=None if enough else "insufficient_view_consensus",
    )
