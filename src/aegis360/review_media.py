"""Resolve event-review samples to bounded, transient render jobs."""

from __future__ import annotations

from typing import Mapping


def build_review_render_jobs(
    packet: Mapping[str, object], grid: Mapping[str, object], *,
    width: int = 384, height: int = 216,
) -> list[dict[str, object]]:
    if isinstance(width, bool) or isinstance(height, bool) or not (
        64 <= width <= 1920 and 64 <= height <= 1080
    ):
        raise ValueError("review-media dimensions are outside the bounded range")
    candidates = {item["candidate_id"]: item for item in grid["candidates"]}
    jobs = []
    for sample in packet["samples"]:
        timestamp = sample["timestamp_seconds"]
        if timestamp is None:
            if sample["candidate_ids"]:
                raise ValueError("missing review timestamp cannot name candidates")
            continue
        for candidate_id in sample["candidate_ids"]:
            if candidate_id not in candidates:
                raise ValueError("review-media candidate is not declared by the grid")
            candidate = candidates[candidate_id]
            jobs.append({
                "sample_id": sample["sample_id"],
                "temporal_role": sample["temporal_role"],
                "timestamp_seconds": timestamp,
                "candidate_id": candidate_id,
                "yaw_degrees": candidate["yaw_degrees"],
                "pitch_degrees": candidate["pitch_degrees"],
                "horizontal_fov_degrees": candidate["horizontal_fov_degrees"],
                "width": width,
                "height": height,
                "filename": f"{sample['sample_id'].replace(':', '-')}-{candidate_id.replace(':', '-')}.png",
            })
    if not 1 <= len(jobs) <= 10:
        raise ValueError("review-media job count is outside the bounded range")
    return jobs


def build_transient_media_index(
    packet: Mapping[str, object], jobs: list[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "aegis360.transient-review-media-index.v1",
        "source_id": packet["source_id"],
        "event_id": packet["event_id"],
        "audio_provided": False,
        "frames": [{
            key: job[key] for key in (
                "sample_id", "temporal_role", "timestamp_seconds",
                "candidate_id", "width", "height", "filename",
            )
        } for job in jobs],
        "lifecycle": "temporary_directory_deleted_after_adapter_exit",
    }
