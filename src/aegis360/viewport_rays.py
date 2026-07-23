"""Convert rectilinear viewport matches into spherical world-ray matches.

The viewport camera uses the project world axes: +Z is yaw/pitch zero, +X is
positive yaw, and +Y is positive pitch.  Pixel coordinates are pixel-center
coordinates with +x right and +y down.  A viewport pose maps camera-local rays
to world rays in yaw, pitch, roll order::

    R_world_from_camera = R_y(+yaw) R_x(-pitch) R_z(+roll)

Roll is therefore a right-handed rotation about the camera's forward (+Z)
axis.  Homographies are row-major 3x3 transforms mapping source pixel
coordinates to target pixel coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .so3 import Ray, rotate_ray

Pixel = tuple[float, float]
RayCorrespondence = tuple[Ray, Ray]


@dataclass(frozen=True)
class RectilinearViewport:
    width: int
    height: int
    yaw: float
    pitch: float
    horizontal_fov: float
    roll: float = 0.0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("viewport dimensions must be positive")
        values = (self.yaw, self.pitch, self.horizontal_fov, self.roll)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("viewport angles must be finite")
        if not -math.pi / 2.0 <= self.pitch <= math.pi / 2.0:
            raise ValueError("viewport pitch must remain between the poles")
        if not 0.0 < self.horizontal_fov < math.pi:
            raise ValueError("horizontal FOV must be in (0, pi)")


def pixel_to_world_ray(pixel: Pixel, viewport: RectilinearViewport) -> Ray:
    """Return the unit world ray through a viewport pixel-center coordinate."""

    x, y = _pixel(pixel, viewport, "pixel")
    base_ray = viewport_normalized_to_world_ray(
        (x + 0.5) / viewport.width,
        (y + 0.5) / viewport.height,
        viewport.yaw,
        viewport.pitch,
        viewport.horizontal_fov,
        viewport.width / viewport.height,
    )
    if viewport.roll == 0.0:
        return base_ray
    # Roll is local, so it must precede yaw and pitch.  Recompute the complete
    # pose rather than rotating the already-world-space ray about world +Z.
    camera_ray = _normalized_camera_ray(
        (x + 0.5) / viewport.width,
        (y + 0.5) / viewport.height,
        viewport.horizontal_fov,
        viewport.width / viewport.height,
    )
    return rotate_ray(_viewport_rotation(viewport.yaw, viewport.pitch, viewport.roll), camera_ray)


def viewport_normalized_to_world_ray(
    x_normalized: float,
    y_normalized: float,
    yaw_radians: float,
    pitch_radians: float,
    horizontal_fov_radians: float,
    aspect_ratio: float,
) -> Ray:
    """Map a normalized rectilinear coordinate to an Aegis world unit ray.

    Normalized image coordinates use top-left origin with both axes spanning
    the closed interval ``[0, 1]``.  Camera-local +Z is forward, +X is image
    right, and +Y is image up.  The world frame uses the same right-handed
    axes.  The returned ray applies active rotations: positive yaw rotates
    forward (+Z) toward +X about world +Y, and positive pitch rotates forward
    toward +Y about the camera-right axis.  The pose is
    ``R_y(+yaw) R_x(-pitch)``.
    """

    values = (
        x_normalized,
        y_normalized,
        yaw_radians,
        pitch_radians,
        horizontal_fov_radians,
        aspect_ratio,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("normalized viewport arguments must be finite")
    if not 0.0 <= x_normalized <= 1.0 or not 0.0 <= y_normalized <= 1.0:
        raise ValueError("normalized coordinates must be in [0, 1]")
    if not -math.pi / 2.0 <= pitch_radians <= math.pi / 2.0:
        raise ValueError("viewport pitch must remain between the poles")
    if not 0.0 < horizontal_fov_radians < math.pi:
        raise ValueError("horizontal FOV must be in (0, pi)")
    if aspect_ratio <= 0.0:
        raise ValueError("aspect ratio must be positive")
    camera_ray = _normalized_camera_ray(
        x_normalized,
        y_normalized,
        horizontal_fov_radians,
        aspect_ratio,
    )
    return rotate_ray(_viewport_rotation(yaw_radians, pitch_radians, 0.0), camera_ray)


def pixel_matches_to_world_rays(
    matches: Iterable[tuple[Pixel, Pixel]],
    source_viewport: RectilinearViewport,
    target_viewport: RectilinearViewport | None = None,
) -> list[RayCorrespondence]:
    """Convert source-to-target pixel matches into world-ray correspondences."""

    target_viewport = target_viewport or source_viewport
    result = []
    for index, (source, target) in enumerate(matches):
        try:
            result.append(
                (
                    pixel_to_world_ray(source, source_viewport),
                    pixel_to_world_ray(target, target_viewport),
                )
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid pixel match at index {index}: {error}") from error
    if not result:
        raise ValueError("at least one pixel match is required")
    return result


def homography_to_world_rays(
    homography_row_major: Sequence[float],
    source_viewport: RectilinearViewport,
    target_viewport: RectilinearViewport | None = None,
    *,
    columns: int = 5,
    rows: int = 3,
) -> list[RayCorrespondence]:
    """Sample a source-to-target homography and return valid ray matches.

    Samples whose projective denominator is zero or whose mapped target lies
    outside the target viewport are omitted.  A wholly unusable transform is
    rejected instead of returning an empty correspondence set.
    """

    target_viewport = target_viewport or source_viewport
    matrix = tuple(homography_row_major)
    if len(matrix) != 9 or not all(math.isfinite(value) for value in matrix):
        raise ValueError("homography must contain nine finite row-major values")
    if columns <= 0 or rows <= 0:
        raise ValueError("homography sample grid dimensions must be positive")

    matches = []
    for row in range(rows):
        y = ((row + 0.5) * source_viewport.height / rows) - 0.5
        for column in range(columns):
            x = ((column + 0.5) * source_viewport.width / columns) - 0.5
            denominator = matrix[6] * x + matrix[7] * y + matrix[8]
            if abs(denominator) <= 1e-12:
                continue
            target = (
                (matrix[0] * x + matrix[1] * y + matrix[2]) / denominator,
                (matrix[3] * x + matrix[4] * y + matrix[5]) / denominator,
            )
            if _inside(target, target_viewport):
                matches.append(((x, y), target))
    if not matches:
        raise ValueError("homography produced no valid viewport correspondences")
    return pixel_matches_to_world_rays(matches, source_viewport, target_viewport)


def _pixel(
    pixel: Pixel, viewport: RectilinearViewport, label: str
) -> tuple[float, float]:
    if len(pixel) != 2 or not all(math.isfinite(value) for value in pixel):
        raise ValueError(f"{label} must contain two finite values")
    if not _inside(pixel, viewport):
        raise ValueError(f"{label} lies outside the viewport")
    return pixel


def _inside(pixel: Pixel, viewport: RectilinearViewport) -> bool:
    x, y = pixel
    return (
        math.isfinite(x)
        and math.isfinite(y)
        and -0.5 <= x <= viewport.width - 0.5
        and -0.5 <= y <= viewport.height - 0.5
    )


def _normalize(vector: tuple[float, float, float]) -> Ray:
    norm = math.sqrt(sum(value * value for value in vector))
    return tuple(value / norm for value in vector)  # type: ignore[return-value]


def _normalized_camera_ray(
    x: float, y: float, horizontal_fov: float, aspect_ratio: float
) -> Ray:
    half_width = math.tan(horizontal_fov / 2.0)
    return _normalize(
        (
            (2.0 * x - 1.0) * half_width,
            (1.0 - 2.0 * y) * half_width / aspect_ratio,
            1.0,
        )
    )


def _viewport_rotation(
    yaw: float, pitch: float, roll: float
) -> tuple[float, float, float, float]:
    return _multiply(
        _axis_angle((0.0, 1.0, 0.0), yaw),
        _multiply(
            _axis_angle((1.0, 0.0, 0.0), -pitch),
            _axis_angle((0.0, 0.0, 1.0), roll),
        ),
    )


def _axis_angle(
    axis: tuple[float, float, float], angle: float
) -> tuple[float, float, float, float]:
    scale = math.sin(angle / 2.0)
    return (
        axis[0] * scale,
        axis[1] * scale,
        axis[2] * scale,
        math.cos(angle / 2.0),
    )


def _multiply(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )
