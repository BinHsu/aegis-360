"""Bounded offline Gaussian smoothing for connected quaternion paths."""

import math

from .so3 import rotation_distance_radians


def smooth_quaternion_path(
    timestamps: list[float],
    orientations: list[list[float] | tuple[float, float, float, float]],
    *,
    radius_seconds: float,
    maximum_correction_radians: float,
) -> list[tuple[float, float, float, float]]:
    if len(timestamps) != len(orientations) or not timestamps:
        raise ValueError("timestamps and orientations must be nonempty and aligned")
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("timestamps must increase")
    if radius_seconds <= 0.0:
        raise ValueError("radius seconds must be positive")
    if not 0.0 < maximum_correction_radians < math.pi:
        raise ValueError("maximum correction must be in (0, pi)")

    path = _continuous_path(orientations)
    sigma = radius_seconds / 2.0
    output = []
    for timestamp, center in zip(timestamps, path):
        weighted = [0.0, 0.0, 0.0, 0.0]
        total = 0.0
        for other_time, sample in zip(timestamps, path):
            delta = abs(other_time - timestamp)
            if delta > radius_seconds:
                continue
            aligned = sample
            if sum(a * b for a, b in zip(center, sample)) < 0.0:
                aligned = tuple(-value for value in sample)
            weight = math.exp(-0.5 * (delta / sigma) ** 2)
            for index, value in enumerate(aligned):
                weighted[index] += weight * value
            total += weight
        smoothed = _unit(tuple(value / total for value in weighted))
        correction = rotation_distance_radians(center, smoothed)
        if correction > maximum_correction_radians:
            smoothed = _slerp(
                center, smoothed, maximum_correction_radians / correction
            )
        if output and sum(a * b for a, b in zip(output[-1], smoothed)) < 0.0:
            smoothed = tuple(-value for value in smoothed)
        output.append(smoothed)
    return output


def _continuous_path(values):
    output = []
    for value in values:
        current = _unit(value)
        if output and sum(a * b for a, b in zip(output[-1], current)) < 0.0:
            current = tuple(-item for item in current)
        output.append(current)
    return output


def _slerp(first, second, fraction):
    left, right = _unit(first), _unit(second)
    dot = sum(a * b for a, b in zip(left, right))
    if dot < 0.0:
        right = tuple(-value for value in right)
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        return _unit(tuple(
            (1.0 - fraction) * a + fraction * b
            for a, b in zip(left, right)
        ))
    angle = math.acos(dot)
    denominator = math.sin(angle)
    return tuple(
        math.sin((1.0 - fraction) * angle) / denominator * a
        + math.sin(fraction * angle) / denominator * b
        for a, b in zip(left, right)
    )


def _unit(value):
    if len(value) != 4 or any(not math.isfinite(item) for item in value):
        raise ValueError("quaternion must contain four finite values")
    norm = math.sqrt(sum(item * item for item in value))
    if norm < 1e-12:
        raise ValueError("quaternion must be nonzero")
    return tuple(item / norm for item in value)
