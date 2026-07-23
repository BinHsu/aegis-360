"""Plan a bounded post-warp stabilization path from flat-video motion evidence.

The Vision probe supplies adjacent-frame registration homographies.  This
module deliberately reduces them to a similarity path: it avoids amplifying
noisy projective terms while retaining translation, rotation, and scale.
"""

from __future__ import annotations

import math
from typing import Sequence


Matrix = tuple[float, float, float, float, float, float, float, float, float]


def multiply(a: Matrix, b: Matrix) -> Matrix:
    return tuple(
        sum(a[row * 3 + k] * b[k * 3 + col] for k in range(3))
        for row in range(3)
        for col in range(3)
    )  # type: ignore[return-value]


def inverse_similarity(matrix: Matrix) -> Matrix:
    a, b, tx, c, d, ty, _, _, _ = matrix
    determinant = a * d - b * c
    if not math.isfinite(determinant) or abs(determinant) < 1e-9:
        raise ValueError("singular similarity matrix")
    return (
        d / determinant, -b / determinant, (b * ty - d * tx) / determinant,
        -c / determinant, a / determinant, (c * tx - a * ty) / determinant,
        0.0, 0.0, 1.0,
    )


def similarity_components(matrix: Sequence[float]) -> tuple[float, float, float, float]:
    if len(matrix) != 9 or not all(math.isfinite(value) for value in matrix):
        raise ValueError("homography must contain nine finite values")
    # Nearest orientation-preserving similarity from the affine 2x2 block.
    x = (matrix[0] + matrix[4]) * 0.5
    y = (matrix[3] - matrix[1]) * 0.5
    scale = math.hypot(x, y)
    if scale < 1e-6:
        raise ValueError("degenerate homography affine block")
    return float(matrix[2]), float(matrix[5]), math.atan2(y, x), math.log(scale)


def similarity_matrix(tx: float, ty: float, angle: float, log_scale: float) -> Matrix:
    scale = math.exp(log_scale)
    cosine = scale * math.cos(angle)
    sine = scale * math.sin(angle)
    return (cosine, -sine, tx, sine, cosine, ty, 0.0, 0.0, 1.0)


def _unwrap(value: float, reference: float) -> float:
    while value - reference > math.pi:
        value -= 2 * math.pi
    while value - reference < -math.pi:
        value += 2 * math.pi
    return value


def smooth_path(
    timestamps: Sequence[float],
    path: Sequence[tuple[float, float, float, float]],
    radius_seconds: float,
) -> list[tuple[float, float, float, float]]:
    if radius_seconds <= 0:
        raise ValueError("smoothing radius must be positive")
    sigma = radius_seconds / 2
    output = []
    for time, center in zip(timestamps, path):
        weighted = [0.0, 0.0, 0.0, 0.0]
        total = 0.0
        for other_time, sample in zip(timestamps, path):
            delta = abs(other_time - time)
            if delta > radius_seconds:
                continue
            weight = math.exp(-0.5 * (delta / sigma) ** 2)
            values = (sample[0], sample[1], _unwrap(sample[2], center[2]), sample[3])
            for index, value in enumerate(values):
                weighted[index] += weight * value
            total += weight
        output.append(tuple(value / total for value in weighted))
    return output  # type: ignore[return-value]


def transform_point(matrix: Matrix, x: float, y: float) -> tuple[float, float]:
    denominator = matrix[6] * x + matrix[7] * y + matrix[8]
    if abs(denominator) < 1e-9:
        raise ValueError("point maps to infinity")
    return (
        (matrix[0] * x + matrix[1] * y + matrix[2]) / denominator,
        (matrix[3] * x + matrix[4] * y + matrix[5]) / denominator,
    )


def plan(
    document: dict[str, object],
    *,
    smoothing_radius_seconds: float,
    measurement_direction: str,
) -> dict[str, object]:
    if measurement_direction not in {"previous_to_current", "current_to_previous"}:
        raise ValueError("unsupported measurement direction")
    observations = document.get("observations")
    if not isinstance(observations, list) or len(observations) < 2:
        raise ValueError("at least two motion observations are required")
    timestamps = [float(row["timestampSeconds"]) for row in observations]
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("observation timestamps must increase")

    identity: Matrix = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    cumulative = identity
    raw_matrices = [identity]
    raw_path = [(0.0, 0.0, 0.0, 0.0)]
    for row in observations[1:]:
        if row.get("state") != "measured":
            step = identity
        else:
            components = similarity_components(row["homographyRowMajor"])
            step = similarity_matrix(*components)
            if measurement_direction == "current_to_previous":
                step = inverse_similarity(step)
        cumulative = multiply(step, cumulative)
        raw_matrices.append(cumulative)
        tx, ty, angle, log_scale = similarity_components(cumulative)
        raw_path.append((tx, ty, _unwrap(angle, raw_path[-1][2]), log_scale))

    smoothed_path = smooth_path(timestamps, raw_path, smoothing_radius_seconds)
    corrections = [
        multiply(similarity_matrix(*smooth), inverse_similarity(raw))
        for raw, smooth in zip(raw_matrices, smoothed_path)
    ]
    width = int(document.get("frameWidth", 0))
    height = int(document.get("frameHeight", 0))
    if width <= 0 or height <= 0:
        raise ValueError("evidence must include positive frameWidth and frameHeight")
    source_corners = ((0.0, 0.0), (width, 0.0), (0.0, height), (width, height))
    frames = []
    maximum_displacement = 0.0
    for index, (time, raw, smooth, correction) in enumerate(
        zip(timestamps, raw_path, smoothed_path, corrections)
    ):
        corners = [transform_point(correction, *corner) for corner in source_corners]
        maximum_displacement = max(
            maximum_displacement,
            *(math.hypot(x - sx, y - sy) for (x, y), (sx, sy) in zip(corners, source_corners)),
        )
        frames.append({
            "frameIndex": index,
            "timestampSeconds": time,
            "rawPath": list(raw),
            "smoothedPath": list(smooth),
            "correctionHomographyRowMajor": list(correction),
            "correctedSourceCorners": [list(corner) for corner in corners],
        })
    margin = min(math.ceil(maximum_displacement), min(width, height) // 3)
    crop = {"x": margin, "y": margin, "width": width - 2 * margin, "height": height - 2 * margin}
    return {
        "schemaVersion": 1,
        "sourceId": document.get("sourceId"),
        "frameWidth": width,
        "frameHeight": height,
        "measurementDirection": measurement_direction,
        "smoothing": {"method": "truncated_gaussian", "radiusSeconds": smoothing_radius_seconds},
        "warpConvention": "row-major source-pixel coordinates; correction maps raw frame to stabilized frame",
        "frames": frames,
        "overscan": {
            "maximumCorrectedCornerDisplacementPixels": maximum_displacement,
            "conservativeSymmetricMarginPixels": margin,
            "recommendedCenteredCrop": crop,
            "note": "Conservative heuristic; validate blank-edge coverage before production use.",
        },
    }
