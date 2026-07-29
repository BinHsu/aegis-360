"""Adapt accepted YOLOX top-left boxes to Apple Vision seed coordinates."""

from __future__ import annotations

import math


def vision_seed_box(detection: dict[str, object]) -> dict[str, float]:
    if detection.get("class_id") not in (0, 1):
        raise ValueError("only accepted person/bicycle detections can seed")
    score = detection.get("score")
    box = detection.get("box")
    if (
        not isinstance(score, (int, float))
        or not math.isfinite(score)
        or score < .25
        or not isinstance(box, list)
        or len(box) != 4
        or not all(isinstance(value, (int, float)) for value in box)
        or not all(math.isfinite(value) for value in box)
    ):
        raise ValueError("accepted YOLOX detection is invalid")
    x, top, width, height = (float(value) for value in box)
    bottom = 1.0 - top - height
    if (
        width <= 0 or height <= 0 or x < 0 or top < 0
        or x + width > 1 or top + height > 1
    ):
        raise ValueError("YOLOX seed box must fit within the viewport")
    return {"x": x, "y": bottom, "width": width, "height": height}
