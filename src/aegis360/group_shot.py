"""Seam-aware contextual framing for simultaneous spherical candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .geometry import spherical_distance, wrap_yaw


@dataclass(frozen=True)
class GroupMember:
    candidate_id: str
    yaw: float
    pitch: float
    horizontal_extent: float


@dataclass(frozen=True)
class GroupShot:
    member_ids: tuple[str, ...]
    yaw: float
    pitch: float
    horizontal_fov: float
    required_horizontal_fov: float
    fully_contains_members: bool


@dataclass(frozen=True)
class GroupShotConfig:
    padding_radians: float = math.radians(10.0)
    minimum_horizontal_fov: float = math.radians(90.0)
    maximum_horizontal_fov: float = math.radians(110.0)

    def __post_init__(self) -> None:
        values = (
            self.padding_radians,
            self.minimum_horizontal_fov,
            self.maximum_horizontal_fov,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("group framing values must be finite")
        if self.padding_radians < 0.0:
            raise ValueError("group padding must be nonnegative")
        if not (
            0.0 < self.minimum_horizontal_fov
            <= self.maximum_horizontal_fov < math.pi
        ):
            raise ValueError("group FOV bounds must be ordered in (0, pi)")


def build_group_shot(
    members: list[GroupMember],
    config: GroupShotConfig = GroupShotConfig(),
) -> GroupShot | None:
    """Return one deterministic wide context shot for two or more members."""

    if len(members) < 2:
        return None
    ordered = sorted(members, key=lambda member: member.candidate_id)
    if (
        len({member.candidate_id for member in ordered}) != len(ordered)
        or any(not member.candidate_id for member in ordered)
    ):
        raise ValueError("group member IDs must be nonempty and unique")
    for member in ordered:
        if not all(math.isfinite(value) for value in (
            member.yaw, member.pitch, member.horizontal_extent
        )):
            raise ValueError("group member geometry must be finite")
        if not -math.pi / 2.0 <= member.pitch <= math.pi / 2.0:
            raise ValueError("group member pitch must remain between poles")
        if not 0.0 <= member.horizontal_extent < math.pi:
            raise ValueError("group member extent must be in [0, pi)")

    vectors = [_unit_vector(member.yaw, member.pitch) for member in ordered]
    summed = tuple(sum(vector[axis] for vector in vectors) for axis in range(3))
    norm = math.sqrt(sum(value * value for value in summed))
    if norm <= 1e-9:
        return None
    center = tuple(value / norm for value in summed)
    yaw = wrap_yaw(math.atan2(center[0], center[2]))
    pitch = math.asin(max(-1.0, min(1.0, center[1])))
    radius = max(
        spherical_distance((yaw, pitch), (member.yaw, member.pitch))
        + member.horizontal_extent / 2.0
        for member in ordered
    )
    required = 2.0 * (radius + config.padding_radians)
    horizontal_fov = min(
        config.maximum_horizontal_fov,
        max(config.minimum_horizontal_fov, required),
    )
    return GroupShot(
        member_ids=tuple(member.candidate_id for member in ordered),
        yaw=yaw,
        pitch=pitch,
        horizontal_fov=horizontal_fov,
        required_horizontal_fov=required,
        fully_contains_members=required <= config.maximum_horizontal_fov,
    )


def build_group_shots(
    members: list[GroupMember],
    config: GroupShotConfig = GroupShotConfig(),
    *,
    maximum_groups: int = 3,
) -> tuple[GroupShot, ...]:
    """Partition nearby members into a bounded set of containable groups."""

    if maximum_groups < 1:
        raise ValueError("maximum groups must be positive")
    ordered = sorted(members, key=lambda member: member.candidate_id)
    # Reuse single-group validation even when no merge will be possible.
    if len(ordered) >= 2:
        build_group_shot(ordered[:2], config)
    clusters = [[member] for member in ordered]
    while True:
        choices = []
        for left in range(len(clusters)):
            for right in range(left + 1, len(clusters)):
                combined = clusters[left] + clusters[right]
                shot = build_group_shot(combined, config)
                if shot is not None and shot.fully_contains_members:
                    choices.append((
                        shot.required_horizontal_fov,
                        shot.member_ids,
                        left,
                        right,
                    ))
        if not choices:
            break
        _, _, left, right = min(choices)
        clusters[left] = sorted(
            clusters[left] + clusters[right],
            key=lambda member: member.candidate_id,
        )
        del clusters[right]

    shots = [
        build_group_shot(cluster, config)
        for cluster in clusters
        if len(cluster) >= 2
    ]
    containable = [shot for shot in shots if shot and shot.fully_contains_members]
    containable.sort(key=lambda shot: (
        -len(shot.member_ids),
        shot.required_horizontal_fov,
        shot.member_ids,
    ))
    return tuple(containable[:maximum_groups])


def _unit_vector(yaw: float, pitch: float) -> tuple[float, float, float]:
    cosine = math.cos(pitch)
    return (
        math.sin(yaw) * cosine,
        math.sin(pitch),
        math.cos(yaw) * cosine,
    )
