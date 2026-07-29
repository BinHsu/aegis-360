"""Privacy-safe detector-refresh trace independent of native backends."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .detector_refresh import RefreshDetection, associate_refresh


@dataclass(frozen=True)
class RefreshEvent:
    timestamp: float
    track_id: str
    track_class: str
    track_yaw: float
    track_pitch: float
    detections: tuple[RefreshDetection, ...]


def build_refresh_trace(
    events: tuple[RefreshEvent, ...],
    *,
    source_id: str,
    maximum_distance: float = math.radians(12.0),
    geometry_policy: str = "strict-v1",
) -> dict[str, object]:
    if (
        not source_id
        or not events
        or geometry_policy not in ("strict-v1", "one-source-pixel-v1")
    ):
        raise ValueError("source ID and refresh events are required")
    previous = -math.inf
    rows = []
    for event in events:
        if (
            not math.isfinite(event.timestamp)
            or event.timestamp <= previous
            or not event.track_id
        ):
            raise ValueError("refresh timestamps and track IDs are invalid")
        result = associate_refresh(
            track_class=event.track_class,
            track_yaw=event.track_yaw,
            track_pitch=event.track_pitch,
            detections=event.detections,
            maximum_distance=maximum_distance,
        )
        rows.append({
            "timestamp": event.timestamp,
            "track_id": event.track_id,
            "track_class": event.track_class,
            "outcome": result.outcome.value,
            "compatible_detection_id": result.compatible_detection_id,
            "compatible_ids": list(result.compatible_ids),
            "editorial_persistence_allowed": False,
            "limitation": result.limitation,
        })
        previous = event.timestamp
    return {
        "schema_version": "aegis360.detector-refresh-trace.v1",
        "source_id": source_id,
        "maximum_distance_degrees": math.degrees(maximum_distance),
        "geometry_policy": geometry_policy,
        "events": rows,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
    }


def dumps_refresh_trace(document: dict[str, object]) -> str:
    return json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
