"""Fit independent tile homographies and select background motion."""

from __future__ import annotations

from dataclasses import dataclass

from .so3 import Ray, RotationFit, fit_rotation
from .tile_motion_consensus import (
    TileMotionConsensus,
    TileRotation,
    select_tile_motion_consensus,
)
from .viewport_rays import (
    RectilinearViewport,
    ViewportTile,
    tile_homography_to_world_ray_samples,
)

RayCorrespondence = tuple[Ray, Ray]


@dataclass(frozen=True)
class TileHomography:
    tile_id: str
    tile: ViewportTile
    homography_row_major: tuple[float, ...]


@dataclass(frozen=True)
class TileFit:
    tile_id: str
    fit: RotationFit
    correspondences: tuple[RayCorrespondence, ...]


@dataclass(frozen=True)
class FittedTileMotion:
    tile_fits: dict[str, TileFit]
    consensus: TileMotionConsensus
    selected_correspondences: tuple[RayCorrespondence, ...]


def fit_tile_motion(
    observations: list[TileHomography],
    viewport: RectilinearViewport,
    *,
    homography_columns: int,
    homography_rows: int,
    maximum_disagreement_radians: float,
    minimum_tiles: int,
    coverage_columns: int,
    coverage_rows: int,
    minimum_covered_cells: int,
) -> FittedTileMotion:
    """Fit each independent tile, then retain a spatially broad cluster."""

    if not observations:
        raise ValueError("at least one tile homography is required")
    identifiers = [observation.tile_id for observation in observations]
    if any(not identifier for identifier in identifiers):
        raise ValueError("tile IDs must be nonempty")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("tile IDs must be unique")

    tile_fits = {}
    rotations = []
    for observation in observations:
        samples = tile_homography_to_world_ray_samples(
            observation.homography_row_major,
            viewport,
            observation.tile,
            columns=homography_columns,
            rows=homography_rows,
        )
        correspondences = tuple(
            (sample["source_ray"], sample["target_ray"])
            for sample in samples
        )
        fitted = fit_rotation(correspondences)
        tile_fits[observation.tile_id] = TileFit(
            tile_id=observation.tile_id,
            fit=fitted,
            correspondences=correspondences,
        )
        rotations.append(TileRotation(
            tile_id=observation.tile_id,
            center_x=(
                observation.tile.x + observation.tile.width / 2.0
            ) / viewport.width,
            center_y=(
                observation.tile.y + observation.tile.height / 2.0
            ) / viewport.height,
            rotation_xyzw=fitted.rotation_xyzw,
        ))

    consensus = select_tile_motion_consensus(
        rotations,
        maximum_disagreement_radians=maximum_disagreement_radians,
        minimum_tiles=minimum_tiles,
        coverage_columns=coverage_columns,
        coverage_rows=coverage_rows,
        minimum_covered_cells=minimum_covered_cells,
    )
    selected = tuple(
        correspondence
        for tile_id in consensus.selected_tile_ids
        for correspondence in tile_fits[tile_id].correspondences
    )
    return FittedTileMotion(
        tile_fits=tile_fits,
        consensus=consensus,
        selected_correspondences=selected,
    )
