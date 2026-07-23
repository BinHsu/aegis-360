"""Spherical geometry using the project's ERP coordinate convention.

Yaw is in ``[-pi, pi)`` after wrapping. Pitch is in ``[-pi/2, pi/2]``.
Pixel coordinates refer to pixel centers and may be fractional when returned
from :func:`angles_to_pixel`.
"""

from __future__ import annotations

import math

TAU = 2.0 * math.pi
HALF_PI = math.pi / 2.0


def _require_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("ERP dimensions must be positive")


def wrap_yaw(yaw: float) -> float:
    """Wrap a finite yaw angle to the half-open interval ``[-pi, pi)``."""

    if not math.isfinite(yaw):
        raise ValueError("yaw must be finite")
    return (yaw + math.pi) % TAU - math.pi


def unwrap_yaw(yaw: float, reference: float) -> float:
    """Return the yaw equivalent nearest to an unwrapped reference yaw."""

    if not math.isfinite(reference):
        raise ValueError("reference must be finite")
    return reference + wrap_yaw(yaw - reference)


def pixel_to_angles(x: float, y: float, width: int, height: int) -> tuple[float, float]:
    """Map an ERP pixel-center coordinate to wrapped yaw and pitch."""

    _require_dimensions(width, height)
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("pixel coordinates must be finite")
    if not (-0.5 <= x <= width - 0.5) or not (-0.5 <= y <= height - 0.5):
        raise ValueError("coordinate lies outside the ERP projection")

    u = (x + 0.5) / width
    v = (y + 0.5) / height
    return wrap_yaw(TAU * u - math.pi), HALF_PI - math.pi * v


def angles_to_pixel(yaw: float, pitch: float, width: int, height: int) -> tuple[float, float]:
    """Map yaw and pitch to a fractional ERP pixel-center coordinate.

    Yaw is periodic. Pitch outside the sphere's latitude range is clamped as
    required by the coordinate contract.
    """

    _require_dimensions(width, height)
    if not math.isfinite(pitch):
        raise ValueError("pitch must be finite")

    u = (wrap_yaw(yaw) + math.pi) / TAU
    clamped_pitch = min(HALF_PI, max(-HALF_PI, pitch))
    v = (HALF_PI - clamped_pitch) / math.pi
    return u * width - 0.5, v * height - 0.5


def direction_from_angles(yaw: float, pitch: float) -> tuple[float, float, float]:
    """Return a unit direction, with yaw zero along +Z and positive toward +X."""

    if not math.isfinite(pitch):
        raise ValueError("pitch must be finite")
    yaw = wrap_yaw(yaw)
    pitch = min(HALF_PI, max(-HALF_PI, pitch))
    cos_pitch = math.cos(pitch)
    return (
        cos_pitch * math.sin(yaw),
        math.sin(pitch),
        cos_pitch * math.cos(yaw),
    )


def spherical_distance(
    first: tuple[float, float], second: tuple[float, float]
) -> float:
    """Return stable great-circle distance between ``(yaw, pitch)`` pairs."""

    a = direction_from_angles(*first)
    b = direction_from_angles(*second)
    cross = (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
    cross_norm = math.sqrt(sum(component * component for component in cross))
    dot = sum(left * right for left, right in zip(a, b))
    return math.atan2(cross_norm, dot)
