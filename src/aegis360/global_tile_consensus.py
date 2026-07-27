"""Fail-closed global rotation consensus across spherical viewport tiles."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .so3 import Quaternion, rotation_distance_radians


@dataclass(frozen=True)
class SphericalTileRotation:
    tile_id: str
    viewport_id: str
    rotation_xyzw: Quaternion


@dataclass(frozen=True)
class GlobalTileConsensus:
    medoid_tile_id: str
    selected_tile_ids: tuple[str, ...]
    selected_viewport_ids: tuple[str, ...]
    rejected_tile_ids: tuple[str, ...]
    state: str
    failure_reason: str | None


def select_global_tile_consensus(
    tiles: list[SphericalTileRotation],
    *,
    maximum_disagreement_radians: float,
    minimum_tiles: int,
    minimum_viewports: int,
) -> GlobalTileConsensus:
    if (
        not math.isfinite(maximum_disagreement_radians)
        or maximum_disagreement_radians < 0.0
    ):
        raise ValueError("maximum disagreement must be finite and nonnegative")
    if minimum_tiles < 1 or minimum_viewports < 1:
        raise ValueError("minimum counts must be positive")
    if not tiles:
        raise ValueError("at least one tile is required")
    by_id = {tile.tile_id: tile for tile in tiles}
    if (
        len(by_id) != len(tiles)
        or any(not tile.tile_id or not tile.viewport_id for tile in tiles)
    ):
        raise ValueError("tile IDs must be unique and IDs must be nonempty")

    identifiers = sorted(by_id)
    medoid = min(
        identifiers,
        key=lambda candidate: (
            sum(
                rotation_distance_radians(
                    by_id[candidate].rotation_xyzw,
                    by_id[other].rotation_xyzw,
                )
                for other in identifiers
            ),
            candidate,
        ),
    )
    selected = tuple(
        identifier for identifier in identifiers
        if rotation_distance_radians(
            by_id[medoid].rotation_xyzw,
            by_id[identifier].rotation_xyzw,
        ) <= maximum_disagreement_radians
    )
    rejected = tuple(
        identifier for identifier in identifiers if identifier not in selected
    )
    viewports = tuple(sorted({
        by_id[identifier].viewport_id for identifier in selected
    }))
    failure = None
    if len(selected) < minimum_tiles:
        failure = "insufficient_global_tile_consensus"
    elif len(viewports) < minimum_viewports:
        failure = "insufficient_global_viewport_coverage"
    return GlobalTileConsensus(
        medoid_tile_id=medoid,
        selected_tile_ids=selected,
        selected_viewport_ids=viewports,
        rejected_tile_ids=rejected,
        state="selected" if failure is None else "invalid",
        failure_reason=failure,
    )
