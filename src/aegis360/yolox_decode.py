"""Dependency-free YOLOX raw-head decode and class-aware NMS contract."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class DecodedDetection:
    class_id: int
    score: float
    box: tuple[float, float, float, float]
    source_index: int


def _iou(left: DecodedDetection, right: DecodedDetection) -> float:
    lx, ly, lw, lh = left.box
    rx, ry, rw, rh = right.box
    intersection = max(0.0, min(lx + lw, rx + rw) - max(lx, rx)) * max(
        0.0, min(ly + lh, ry + rh) - max(ly, ry)
    )
    union = lw * lh + rw * rh - intersection
    return 0.0 if union <= 0 else intersection / union


def decode_yolox(
    rows: Sequence[Sequence[float]],
    *,
    input_size: int = 416,
    strides: tuple[int, ...] = (8, 16, 32),
    confidence_threshold: float = .25,
    nms_iou_threshold: float = .45,
) -> tuple[DecodedDetection, ...]:
    if (
        input_size <= 0
        or not 0 <= confidence_threshold <= 1
        or not 0 <= nms_iou_threshold <= 1
    ):
        raise ValueError("decode configuration is invalid")
    grids = [
        (x, y, stride)
        for stride in strides
        for y in range(input_size // stride)
        for x in range(input_size // stride)
    ]
    if len(rows) != len(grids):
        raise ValueError("raw row count does not match YOLOX grids")
    candidates = []
    for index, (row, (grid_x, grid_y, stride)) in enumerate(zip(rows, grids)):
        if len(row) != 85 or not all(math.isfinite(float(value)) for value in row):
            raise ValueError("each YOLOX row must contain 85 finite values")
        class_id = max(range(80), key=lambda item: (float(row[5 + item]), -item))
        score = float(row[4]) * float(row[5 + class_id])
        if score < confidence_threshold:
            continue
        center_x = (float(row[0]) + grid_x) * stride
        center_y = (float(row[1]) + grid_y) * stride
        width = math.exp(float(row[2])) * stride
        height = math.exp(float(row[3])) * stride
        candidates.append(DecodedDetection(
            class_id,
            score,
            (
                (center_x - width / 2) / input_size,
                (center_y - height / 2) / input_size,
                width / input_size,
                height / input_size,
            ),
            index,
        ))
    retained = []
    for candidate in sorted(
        candidates, key=lambda item: (-item.score, item.class_id, item.source_index)
    ):
        if all(
            candidate.class_id != prior.class_id
            or _iou(candidate, prior) <= nms_iou_threshold
            for prior in retained
        ):
            retained.append(candidate)
    return tuple(retained)


def detection_document(
    detections: tuple[DecodedDetection, ...],
) -> list[dict[str, object]]:
    return [{
        "class_id": detection.class_id,
        "score": detection.score,
        "box": list(detection.box),
    } for detection in detections]
