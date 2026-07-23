"""Calibrated conversion of Apple Vision registration homographies.

``VNTrackHomographicImageRegistrationRequest`` reports a transform that maps
the current (target) image into the reference (source) image in a bottom-left
pixel coordinate system.  Aegis geometry consumes the inverse relation:
source to target in top-left pixel-center coordinates.

This module makes both changes explicit.  It intentionally does not infer the
convention from the observed translation because doing so would make signs
ambiguous for rotations and projective transforms.
"""

from __future__ import annotations

import math
from typing import Sequence


def vision_native_to_source_target_top_left(
    native_row_major: Sequence[float], frame_height: int
) -> tuple[float, ...]:
    """Convert Vision-native registration into Aegis pixel coordinates.

    ``native_row_major`` maps target-bottom-left pixels to
    source-bottom-left pixels.  The returned row-major homography maps
    source-top-left pixels to target-top-left pixels.  Pixel centers span
    ``0 .. frame_height - 1``, hence the vertical basis change uses
    ``frame_height - 1``.
    """

    native = tuple(native_row_major)
    if len(native) != 9 or not all(math.isfinite(value) for value in native):
        raise ValueError("Vision homography must contain nine finite values")
    if frame_height <= 0:
        raise ValueError("frame height must be positive")
    vertical_flip = (
        1.0, 0.0, 0.0,
        0.0, -1.0, float(frame_height - 1),
        0.0, 0.0, 1.0,
    )
    # C^-1 == C.  First express target->source in top-left coordinates,
    # then invert it to obtain the source->target relation used by ray fitting.
    target_to_source_top_left = _multiply(
        vertical_flip, _multiply(native, vertical_flip)
    )
    source_to_target = _inverse(target_to_source_top_left)
    scale = source_to_target[8]
    if abs(scale) <= 1e-12:
        raise ValueError("converted Vision homography has zero projective scale")
    return tuple(value / scale for value in source_to_target)


def _multiply(first: Sequence[float], second: Sequence[float]) -> tuple[float, ...]:
    return tuple(
        sum(first[row * 3 + index] * second[index * 3 + column]
            for index in range(3))
        for row in range(3)
        for column in range(3)
    )


def _inverse(matrix: Sequence[float]) -> tuple[float, ...]:
    a, b, c, d, e, f, g, h, i = matrix
    cofactors = (
        e * i - f * h, c * h - b * i, b * f - c * e,
        f * g - d * i, a * i - c * g, c * d - a * f,
        d * h - e * g, b * g - a * h, a * e - b * d,
    )
    determinant = a * cofactors[0] + b * cofactors[3] + c * cofactors[6]
    if abs(determinant) <= 1e-12:
        raise ValueError("Vision homography is singular")
    return tuple(value / determinant for value in cofactors)
