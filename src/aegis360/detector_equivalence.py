"""Vendor-neutral numerical equivalence checks for detector conversion."""

from __future__ import annotations

import math


def _iou(left: object, right: object) -> float:
    if (
        not isinstance(left, list) or not isinstance(right, list)
        or len(left) != 4 or len(right) != 4
        or not all(isinstance(value, (int, float)) for value in left + right)
    ):
        raise ValueError("boxes must be [x, y, width, height]")
    if not all(math.isfinite(value) for value in left + right):
        raise ValueError("box values must be finite")
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    if min(lw, lh, rw, rh) < 0:
        raise ValueError("box extents must be nonnegative")
    intersection = max(0.0, min(lx + lw, rx + rw) - max(lx, rx)) * max(
        0.0, min(ly + lh, ry + rh) - max(ly, ry)
    )
    union = lw * lh + rw * rh - intersection
    return 1.0 if union == 0 else intersection / union


def compare_detector_outputs(
    reference: dict[str, object],
    candidate: dict[str, object],
    *,
    maximum_absolute_error: float = .02,
    maximum_mean_absolute_error: float = .005,
    minimum_top_agreement: int = 19,
    top_count: int = 20,
    minimum_box_iou: float = .95,
    maximum_score_error: float = .03,
) -> dict[str, object]:
    """Compare frozen raw tensors and already-decoded ordered detections."""

    reference_tensors = reference.get("tensors")
    candidate_tensors = candidate.get("tensors")
    if not isinstance(reference_tensors, list) or not isinstance(
        candidate_tensors, list
    ) or len(reference_tensors) != len(candidate_tensors):
        raise ValueError("tensor collections must have equal nonempty structure")
    errors: list[float] = []
    top_agreements = []
    required_top_agreements = []
    for left, right in zip(reference_tensors, candidate_tensors):
        if (
            not isinstance(left, dict) or not isinstance(right, dict)
            or left.get("name") != right.get("name")
            or left.get("shape") != right.get("shape")
        ):
            raise ValueError("tensor names and shapes must match")
        left_values = left.get("values")
        right_values = right.get("values")
        if (
            not isinstance(left_values, list)
            or not isinstance(right_values, list)
            or len(left_values) != len(right_values)
            or not left_values
            or not all(isinstance(value, (int, float)) for value in left_values)
            or not all(isinstance(value, (int, float)) for value in right_values)
        ):
            raise ValueError("tensor values must be equal-length numeric lists")
        if not all(math.isfinite(value) for value in left_values + right_values):
            raise ValueError("tensor values must be finite")
        errors.extend(abs(a - b) for a, b in zip(left_values, right_values))
        count = min(top_count, len(left_values))
        left_top = set(sorted(
            range(len(left_values)), key=lambda index: (-left_values[index], index)
        )[:count])
        right_top = set(sorted(
            range(len(right_values)), key=lambda index: (-right_values[index], index)
        )[:count])
        top_agreements.append(len(left_top & right_top))
        required_top_agreements.append(
            min(minimum_top_agreement, top_count, count)
        )

    left_detections = reference.get("detections")
    right_detections = candidate.get("detections")
    if not isinstance(left_detections, list) or not isinstance(
        right_detections, list
    ) or len(left_detections) != len(right_detections):
        raise ValueError("decoded detection counts must match")
    decoded_pass = True
    decoded_rows = []
    for left, right in zip(left_detections, right_detections):
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("detections must be objects")
        class_match = left.get("class_id") == right.get("class_id")
        left_score, right_score = left.get("score"), right.get("score")
        if not isinstance(left_score, (int, float)) or not isinstance(
            right_score, (int, float)
        ) or not all(math.isfinite(value) for value in (left_score, right_score)):
            raise ValueError("detection scores must be finite")
        score_error = abs(left_score - right_score)
        box_iou = _iou(left.get("box"), right.get("box"))
        passed = (
            class_match and score_error <= maximum_score_error
            and box_iou >= minimum_box_iou
        )
        decoded_pass &= passed
        decoded_rows.append({
            "class_match": class_match,
            "score_absolute_error": score_error,
            "box_iou": box_iou,
            "passed": passed,
        })

    maximum = max(errors)
    mean = sum(errors) / len(errors)
    raw_pass = (
        maximum <= maximum_absolute_error
        and mean <= maximum_mean_absolute_error
        and all(
            agreement >= required
            for agreement, required in zip(
                top_agreements, required_top_agreements
            )
        )
    )
    return {
        "schema_version": "aegis360.detector-equivalence-report.v1",
        "passed": raw_pass and decoded_pass,
        "raw": {
            "maximum_absolute_error": maximum,
            "mean_absolute_error": mean,
            "top_index_agreements": top_agreements,
            "passed": raw_pass,
        },
        "decoded": {"comparisons": decoded_rows, "passed": decoded_pass},
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
    }
