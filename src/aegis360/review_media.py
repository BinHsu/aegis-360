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


def build_story_review_render_jobs(
    packet: Mapping[str, object], grid: Mapping[str, object], *,
    width: int = 384, height: int = 216,
) -> list[dict[str, object]]:
    """Resolve one composite job per story sample, with four owned viewports."""
    accepted = {"aegis360.scene-story-review-packet.v1",
                "aegis360.story-segment-review-packet.v1"}
    if packet.get("schema_version") not in accepted:
        raise ValueError("story review packet schema is invalid")
    if isinstance(width, bool) or isinstance(height, bool) or not (
        64 <= width <= 960 and 64 <= height <= 540
    ):
        raise ValueError("story review viewport dimensions are outside the bounded range")
    candidates = {item["candidate_id"]: item for item in grid["candidates"]}
    jobs = []
    for sample in packet["samples"]:
        candidate_ids = sample.get("candidate_ids")
        if (sample.get("representation") != "four_cardinal_contact_sheet"
                or len(candidate_ids or []) != 4
                or any(candidate_id not in candidates for candidate_id in candidate_ids)):
            raise ValueError("story review sample is not a declared cardinal composite")
        viewports = []
        for candidate_id in candidate_ids:
            candidate = candidates[candidate_id]
            viewports.append({
                "candidate_id": candidate_id,
                "yaw_degrees": candidate["yaw_degrees"],
                "pitch_degrees": candidate["pitch_degrees"],
                "horizontal_fov_degrees": candidate["horizontal_fov_degrees"],
            })
        jobs.append({
            "sample_id": sample["sample_id"], "temporal_role": sample["temporal_role"],
            "timestamp_seconds": sample["timestamp_seconds"], "viewports": viewports,
            "viewport_width": width, "viewport_height": height,
            "width": width * 2, "height": height * 2,
            "filename": f"{sample['sample_id'].replace(':', '-')}-cardinal-contact.png",
        })
    minimum, maximum = ((2, 6) if packet["schema_version"] ==
                        "aegis360.scene-story-review-packet.v1" else (3, 3))
    if not minimum <= len(jobs) <= maximum or len(jobs) * 4 > maximum * 4:
        raise ValueError("story review jobs exceed the bounded contract")
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


def build_story_transient_media_index(
    packet: Mapping[str, object], jobs: list[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": ("aegis360.transient-story-review-media-index.v1"
                           if "event_id" in packet else
                           "aegis360.transient-story-segment-review-media-index.v1"),
        "source_id": packet["source_id"],
        **({"event_id": packet["event_id"]} if "event_id" in packet else
           {"segment_id": packet["segment_id"]}),
        "audio_provided": False,
        "frames": [{
            "sample_id": job["sample_id"], "temporal_role": job["temporal_role"],
            "timestamp_seconds": job["timestamp_seconds"],
            "representation": "four_cardinal_contact_sheet",
            "candidate_ids": [item["candidate_id"] for item in job["viewports"]],
            "width": job["width"], "height": job["height"],
            "filename": job["filename"],
        } for job in jobs],
        "lifecycle": "temporary_directory_deleted_after_adapter_exit",
    }
