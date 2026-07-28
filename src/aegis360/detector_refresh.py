"""Fail-closed association between a live track and detector refreshes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .geometry import spherical_distance


class RefreshOutcome(str, Enum):
    COMPATIBLE = "compatible_not_identity_verified"
    AMBIGUOUS = "ambiguous_multiple_compatible"
    MISSING = "no_compatible_detection"


@dataclass(frozen=True)
class RefreshDetection:
    detection_id: str
    semantic_class: str
    yaw: float
    pitch: float

    def __post_init__(self) -> None:
        if not self.detection_id or not self.semantic_class:
            raise ValueError("detection ID and class must be nonempty")
        if not all(math.isfinite(value) for value in (self.yaw, self.pitch)):
            raise ValueError("detection direction must be finite")
        if not -math.pi / 2 <= self.pitch <= math.pi / 2:
            raise ValueError("detection pitch is outside the sphere")


@dataclass(frozen=True)
class RefreshResult:
    outcome: RefreshOutcome
    compatible_detection_id: str | None
    compatible_ids: tuple[str, ...]
    limitation: str = (
        "Class and geometry compatibility do not establish persistent identity."
    )


def associate_refresh(
    *,
    track_class: str,
    track_yaw: float,
    track_pitch: float,
    detections: tuple[RefreshDetection, ...],
    maximum_distance: float = math.radians(12.0),
) -> RefreshResult:
    if not track_class:
        raise ValueError("track class must be nonempty")
    if (
        not all(math.isfinite(value) for value in (track_yaw, track_pitch))
        or not -math.pi / 2 <= track_pitch <= math.pi / 2
        or not math.isfinite(maximum_distance)
        or maximum_distance <= 0
        or maximum_distance >= math.pi
    ):
        raise ValueError("track direction or maximum distance is invalid")
    compatible = tuple(sorted(
        (
            detection.detection_id
            for detection in detections
            if detection.semantic_class == track_class
            and spherical_distance(
                (track_yaw, track_pitch), (detection.yaw, detection.pitch)
            ) <= maximum_distance
        )
    ))
    if not compatible:
        return RefreshResult(RefreshOutcome.MISSING, None, ())
    if len(compatible) > 1:
        return RefreshResult(RefreshOutcome.AMBIGUOUS, None, compatible)
    return RefreshResult(RefreshOutcome.COMPATIBLE, compatible[0], compatible)
