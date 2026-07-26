"""Deterministic background-motion consensus from independent image tiles."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .so3 import Quaternion, rotation_distance_radians


@dataclass(frozen=True)
class TileRotation:
    tile_id: str
    center_x: float
    center_y: float
    rotation_xyzw: Quaternion


@dataclass(frozen=True)
class TileMotionConsensus:
    medoid_tile_id: str
    selected_tile_ids: tuple[str, ...]
    rejected_tile_ids: tuple[str, ...]
    covered_cell_ids: tuple[str, ...]
    medoid_distances_radians: dict[str, float]
    state: str
    failure_reason: str | None


def select_tile_motion_consensus(
    tiles: list[TileRotation],
    *,
    maximum_disagreement_radians: float,
    minimum_tiles: int,
    coverage_columns: int,
    coverage_rows: int,
    minimum_covered_cells: int,
) -> TileMotionConsensus:
    """Select a rotation cluster and require it to span the image.

    Each input must come from an independently registered tile. Spatial
    coverage prevents a coherent local foreground patch from being accepted
    merely because several adjacent tiles agree with each other.
    """

    if not math.isfinite(maximum_disagreement_radians):
        raise ValueError("maximum disagreement must be finite")
    if maximum_disagreement_radians < 0.0:
        raise ValueError("maximum disagreement must be nonnegative")
    if minimum_tiles < 1:
        raise ValueError("minimum tiles must be positive")
    if coverage_columns < 1 or coverage_rows < 1:
        raise ValueError("coverage grid dimensions must be positive")
    cell_count = coverage_columns * coverage_rows
    if not 1 <= minimum_covered_cells <= cell_count:
        raise ValueError("minimum covered cells is out of range")
    if not tiles:
        raise ValueError("at least one tile is required")

    by_id = {tile.tile_id: tile for tile in tiles}
    if len(by_id) != len(tiles) or any(not tile.tile_id for tile in tiles):
        raise ValueError("tile IDs must be nonempty and unique")
    if any(
        not math.isfinite(value) or not 0.0 <= value <= 1.0
        for tile in tiles
        for value in (tile.center_x, tile.center_y)
    ):
        raise ValueError("tile centers must be finite normalized coordinates")

    tile_ids = sorted(by_id)
    medoid_id = min(
        tile_ids,
        key=lambda candidate: (
            sum(
                rotation_distance_radians(
                    by_id[candidate].rotation_xyzw,
                    by_id[other].rotation_xyzw,
                )
                for other in tile_ids
            ),
            candidate,
        ),
    )
    distances = {
        tile_id: rotation_distance_radians(
            by_id[medoid_id].rotation_xyzw,
            by_id[tile_id].rotation_xyzw,
        )
        for tile_id in tile_ids
    }
    selected = tuple(
        tile_id for tile_id in tile_ids
        if distances[tile_id] <= maximum_disagreement_radians
    )
    rejected = tuple(tile_id for tile_id in tile_ids if tile_id not in selected)
    cells = tuple(sorted({
        _cell_id(
            by_id[tile_id], coverage_columns=coverage_columns,
            coverage_rows=coverage_rows,
        )
        for tile_id in selected
    }))

    failure_reason = None
    if len(selected) < minimum_tiles:
        failure_reason = "insufficient_tile_consensus"
    elif len(cells) < minimum_covered_cells:
        failure_reason = "insufficient_spatial_coverage"
    return TileMotionConsensus(
        medoid_tile_id=medoid_id,
        selected_tile_ids=selected,
        rejected_tile_ids=rejected,
        covered_cell_ids=cells,
        medoid_distances_radians=distances,
        state="selected" if failure_reason is None else "invalid",
        failure_reason=failure_reason,
    )


def _cell_id(
    tile: TileRotation, *, coverage_columns: int, coverage_rows: int
) -> str:
    column = min(int(tile.center_x * coverage_columns), coverage_columns - 1)
    row = min(int(tile.center_y * coverage_rows), coverage_rows - 1)
    return f"r{row}c{column}"
