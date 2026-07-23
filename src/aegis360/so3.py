"""Dependency-free robust rotation fitting for spherical ray matches.

The fitted quaternion is in ``(x, y, z, w)`` order and represents the active
right-handed rotation that maps each source ray to its corresponding target
ray.  This matches the orientation semantics in
``docs/design/spherical-stabilization-and-segment-policy.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

Ray = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


@dataclass(frozen=True)
class RotationFit:
    rotation_xyzw: Quaternion
    confidence: float
    residual_radians: float
    inlier_ratio: float
    inlier_count: int
    correspondence_count: int
    iterations: int


def rotate_ray(rotation_xyzw: Quaternion, ray: Ray) -> Ray:
    """Apply an active unit-quaternion rotation to a unit ray."""

    x, y, z, w = _unit_quaternion(rotation_xyzw)
    vx, vy, vz = _unit_ray(ray, "ray")
    # q v q^-1, expanded to avoid temporary quaternion allocations.
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    )


def fit_rotation(
    correspondences: Iterable[tuple[Ray, Ray]],
    *,
    max_iterations: int = 12,
    inlier_threshold_radians: float = math.radians(3.0),
) -> RotationFit:
    """Robustly fit the rotation mapping source rays to target rays.

    Davenport's q-method solves each weighted Wahba problem.  Iteratively
    reweighted Tukey weights suppress mismatches.  Confidence intentionally
    combines inlier fraction, angular coverage, and residual quality; it is a
    diagnostic score, not a calibrated probability.
    """

    pairs = [
        (_unit_ray(source, "source ray"), _unit_ray(target, "target ray"))
        for source, target in correspondences
    ]
    if len(pairs) < 2:
        raise ValueError("at least two ray correspondences are required")
    if max(
        math.sqrt(max(0.0, 1.0 - _dot(first[0], second[0]) ** 2))
        for index, first in enumerate(pairs)
        for second in pairs[index + 1 :]
    ) < 1e-4:
        raise ValueError("source rays have insufficient angular diversity")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")
    if (
        not math.isfinite(inlier_threshold_radians)
        or inlier_threshold_radians <= 0.0
        or inlier_threshold_radians >= math.pi
    ):
        raise ValueError("inlier threshold must be finite and in (0, pi)")

    weights = [1.0] * len(pairs)
    rotation = (0.0, 0.0, 0.0, 1.0)
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        rotation = _davenport(pairs, weights)
        residuals = _residuals(rotation, pairs)
        median = _median(residuals)
        deviations = [abs(value - median) for value in residuals]
        # 1.4826 converts MAD to a Gaussian sigma estimate.  The floor keeps
        # exact synthetic data from rejecting tiny floating-point residuals.
        scale = max(1.4826 * _median(deviations), inlier_threshold_radians / 6.0)
        cutoff = max(inlier_threshold_radians, 4.685 * scale)
        updated = []
        for residual in residuals:
            ratio = residual / cutoff
            updated.append((1.0 - ratio * ratio) ** 2 if ratio < 1.0 else 0.0)
        if sum(weight > 0.0 for weight in updated) < 2:
            break
        change = max(abs(a - b) for a, b in zip(weights, updated))
        weights = updated
        if change < 1e-7:
            rotation = _davenport(pairs, weights)
            break

    residuals = _residuals(rotation, pairs)
    inliers = [value <= inlier_threshold_radians for value in residuals]
    inlier_values = [
        residual for residual, is_inlier in zip(residuals, inliers) if is_inlier
    ]
    inlier_count = len(inlier_values)
    inlier_ratio = inlier_count / len(pairs)
    residual = (
        math.sqrt(sum(value * value for value in inlier_values) / inlier_count)
        if inlier_values
        else math.pi
    )
    coverage = _coverage([source for (source, _), flag in zip(pairs, inliers) if flag])
    quality = max(0.0, 1.0 - residual / inlier_threshold_radians)
    confidence = max(0.0, min(1.0, inlier_ratio * coverage * quality))
    return RotationFit(
        rotation_xyzw=rotation,
        confidence=confidence,
        residual_radians=residual,
        inlier_ratio=inlier_ratio,
        inlier_count=inlier_count,
        correspondence_count=len(pairs),
        iterations=iterations,
    )


def _davenport(
    pairs: Sequence[tuple[Ray, Ray]], weights: Sequence[float]
) -> Quaternion:
    # Davenport's convention below uses B = sum(source * target^T) for the
    # active quaternion that maps source into target.
    b = [[0.0] * 3 for _ in range(3)]
    for (source, target), weight in zip(pairs, weights):
        for row in range(3):
            for column in range(3):
                b[row][column] += weight * source[row] * target[column]
    sigma = b[0][0] + b[1][1] + b[2][2]
    symmetric = [[b[i][j] + b[j][i] for j in range(3)] for i in range(3)]
    z = (
        b[1][2] - b[2][1],
        b[2][0] - b[0][2],
        b[0][1] - b[1][0],
    )
    matrix = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        for j in range(3):
            matrix[i][j] = symmetric[i][j] - (sigma if i == j else 0.0)
        matrix[i][3] = z[i]
        matrix[3][i] = z[i]
    matrix[3][3] = sigma
    eigenvalues, eigenvectors = _symmetric_eigen(matrix)
    index = max(range(4), key=lambda item: eigenvalues[item])
    quaternion = tuple(eigenvectors[row][index] for row in range(4))
    return _canonical_quaternion(quaternion)  # type: ignore[arg-type]


def _symmetric_eigen(
    matrix: Sequence[Sequence[float]],
) -> tuple[list[float], list[list[float]]]:
    """Jacobi eigendecomposition for the fixed, symmetric 4x4 Davenport matrix."""

    size = len(matrix)
    values = [list(row) for row in matrix]
    vectors = [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]
    for _ in range(64):
        p, q = max(
            ((i, j) for i in range(size) for j in range(i + 1, size)),
            key=lambda pair: abs(values[pair[0]][pair[1]]),
        )
        if abs(values[p][q]) < 1e-15:
            break
        angle = 0.5 * math.atan2(
            2.0 * values[p][q], values[q][q] - values[p][p]
        )
        cosine, sine = math.cos(angle), math.sin(angle)
        for i in range(size):
            if i not in (p, q):
                aip, aiq = values[i][p], values[i][q]
                values[i][p] = values[p][i] = cosine * aip - sine * aiq
                values[i][q] = values[q][i] = sine * aip + cosine * aiq
        app, aqq, apq = values[p][p], values[q][q], values[p][q]
        values[p][p] = cosine * cosine * app - 2 * sine * cosine * apq + sine * sine * aqq
        values[q][q] = sine * sine * app + 2 * sine * cosine * apq + cosine * cosine * aqq
        values[p][q] = values[q][p] = 0.0
        for i in range(size):
            vip, viq = vectors[i][p], vectors[i][q]
            vectors[i][p] = cosine * vip - sine * viq
            vectors[i][q] = sine * vip + cosine * viq
    return [values[i][i] for i in range(size)], vectors


def _residuals(
    rotation: Quaternion, pairs: Sequence[tuple[Ray, Ray]]
) -> list[float]:
    result = []
    for source, target in pairs:
        predicted = rotate_ray(rotation, source)
        cross = (
            predicted[1] * target[2] - predicted[2] * target[1],
            predicted[2] * target[0] - predicted[0] * target[2],
            predicted[0] * target[1] - predicted[1] * target[0],
        )
        result.append(
            math.atan2(
                math.sqrt(sum(value * value for value in cross)),
                _dot(predicted, target),
            )
        )
    return result


def _coverage(rays: Sequence[Ray]) -> float:
    """Return 0..1 angular spread; antipodal/wide observations approach one."""

    if len(rays) < 2:
        return 0.0
    maximum = max(
        math.acos(max(-1.0, min(1.0, _dot(first, second))))
        for index, first in enumerate(rays)
        for second in rays[index + 1 :]
    )
    return min(1.0, maximum / (math.pi / 2.0))


def _unit_ray(ray: Sequence[float], label: str) -> Ray:
    if len(ray) != 3 or not all(math.isfinite(value) for value in ray):
        raise ValueError(f"{label} must contain three finite values")
    norm = math.sqrt(sum(value * value for value in ray))
    if not math.isclose(norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        raise ValueError(f"{label} must be unit length")
    return (ray[0] / norm, ray[1] / norm, ray[2] / norm)


def _unit_quaternion(quaternion: Sequence[float]) -> Quaternion:
    if len(quaternion) != 4 or not all(math.isfinite(value) for value in quaternion):
        raise ValueError("quaternion must contain four finite values")
    norm = math.sqrt(sum(value * value for value in quaternion))
    if norm <= 1e-15:
        raise ValueError("quaternion must be nonzero")
    return tuple(value / norm for value in quaternion)  # type: ignore[return-value]


def _canonical_quaternion(quaternion: Quaternion) -> Quaternion:
    result = _unit_quaternion(quaternion)
    return tuple(-value for value in result) if result[3] < 0.0 else result  # type: ignore[return-value]


def _dot(first: Ray, second: Ray) -> float:
    return sum(left * right for left, right in zip(first, second))


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])
