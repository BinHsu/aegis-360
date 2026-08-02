"""Tunable subject-framing quality gate for semantic detector events."""

from __future__ import annotations

from dataclasses import dataclass
import copy
import math
from typing import Mapping

from .semantic_events import SCHEMA_VERSION


@dataclass(frozen=True)
class SubjectFramingQualityPolicy:
    maximum_box_width_fraction: float = 0.9
    maximum_box_height_fraction: float = 0.9

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value) and 0 < value <= 1
            for value in (
                self.maximum_box_width_fraction,
                self.maximum_box_height_fraction,
            )
        ):
            raise ValueError("framing quality thresholds must be in (0, 1]")


def filter_subject_framing_events(
    document: Mapping[str, object],
    policy: SubjectFramingQualityPolicy = SubjectFramingQualityPolicy(),
) -> tuple[dict[str, object], dict[str, object]]:
    """Quarantine oversized boxes without calling them detector false positives."""

    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported semantic event schema")
    events = document.get("events")
    if not isinstance(events, list):
        raise ValueError("events must be an array")
    accepted = copy.deepcopy(dict(document))
    accepted_events = accepted.get("events")
    assert isinstance(accepted_events, list)
    quarantined = []
    for source_event, accepted_event in zip(events, accepted_events):
        if not isinstance(source_event, Mapping) or not isinstance(accepted_event, dict):
            raise ValueError("event must be an object")
        detections = source_event.get("detections")
        if not isinstance(detections, list):
            raise ValueError("detections must be an array")
        retained = []
        for detection in detections:
            if not isinstance(detection, Mapping):
                raise ValueError("detection must be an object")
            box = detection.get("box_top_left_normalized")
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError("detection box is invalid")
            width = box[2]
            height = box[3]
            if (
                not isinstance(width, (int, float)) or isinstance(width, bool)
                or not isinstance(height, (int, float)) or isinstance(height, bool)
                or not math.isfinite(width) or not math.isfinite(height)
            ):
                raise ValueError("detection box dimensions are invalid")
            reasons = []
            if width >= policy.maximum_box_width_fraction:
                reasons.append("box_width_at_or_above_subject_limit")
            if height >= policy.maximum_box_height_fraction:
                reasons.append("box_height_at_or_above_subject_limit")
            if reasons:
                quarantined.append({
                    "timestamp_seconds": source_event.get("timestamp_seconds"),
                    "viewport_id": source_event.get("viewport_id"),
                    "class_name": detection.get("class_name"),
                    "source_index": detection.get("source_index"),
                    "reasons": reasons,
                })
            else:
                retained.append(copy.deepcopy(dict(detection)))
        accepted_event["detections"] = retained
    report = {
        "schema_version": "aegis360.subject-framing-quality.v1",
        "policy": {
            "maximum_box_width_fraction": policy.maximum_box_width_fraction,
            "maximum_box_height_fraction": policy.maximum_box_height_fraction,
            "classification": "unsuitable_for_subject_framing_not_detector_false_positive",
        },
        "accepted_detection_count": sum(
            len(event["detections"]) for event in accepted_events
        ),
        "quarantined_detection_count": len(quarantined),
        "quarantined": quarantined,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
    }
    return accepted, report
