"""Pure mechanical checks for equal-contract reaction preview peers."""

from __future__ import annotations

import math
from typing import Mapping


def _yaw_distance(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def evaluate_reaction_preview(
    grid: Mapping[str, object], roles: Mapping[str, object], plan: Mapping[str, object],
    primary_trace: Mapping[str, object], planned_trace: Mapping[str, object],
    primary_probe: Mapping[str, object], planned_probe: Mapping[str, object], *,
    primary_video_hash: str, planned_video_hash: str,
    primary_audio_hash: str, planned_audio_hash: str,
    minimum_pose_change_degrees: float = 8.0,
    minimum_distinct_seconds: float = 2.0,
) -> dict[str, object]:
    if minimum_pose_change_degrees < 0 or minimum_distinct_seconds < 0:
        raise ValueError("pre-review thresholds must be nonnegative")
    assignments = {item["role"]: item["candidate_id"] for item in roles["assignments"]}
    primary_id = assignments["primary_performance"]
    candidates = {item["candidate_id"]: item for item in grid["candidates"]}
    expected_primary = [{
        "start_seconds": grid["window"]["start_seconds"],
        "end_seconds": grid["window"]["start_seconds"] + grid["window"]["duration_seconds"],
        "candidate_id": primary_id, "reason": "primary_only_baseline",
    }]
    trace_binding = (
        primary_trace.get("mode") == "primary-only" and
        planned_trace.get("mode") == "planned" and
        primary_trace.get("segments") == expected_primary and
        planned_trace.get("segments") == plan["segments"] and
        primary_trace.get("source_id") == grid["source_id"] and
        planned_trace.get("source_id") == grid["source_id"] and
        primary_trace.get("context_view_grid_sha256") == planned_trace.get("context_view_grid_sha256") and
        primary_trace.get("reaction_shot_plan_sha256") == planned_trace.get("reaction_shot_plan_sha256")
    )
    encoder_equal = primary_trace.get("encoder") == planned_trace.get("encoder")
    probe_equal = primary_probe == planned_probe
    audio_equal = primary_audio_hash == planned_audio_hash
    promoted = [item for item in plan["segments"] if item["candidate_id"] != primary_id]
    distinct_seconds = sum(item["end_seconds"] - item["start_seconds"] for item in promoted)
    primary_view = candidates[primary_id]
    pose_changes = []
    for item in promoted:
        proposed = candidates[item["candidate_id"]]
        pose_changes.append(max(
            _yaw_distance(proposed["yaw_degrees"], primary_view["yaw_degrees"]),
            abs(proposed["pitch_degrees"] - primary_view["pitch_degrees"]),
            abs(proposed["horizontal_fov_degrees"] - primary_view["horizontal_fov_degrees"]),
        ))
    maximum_pose_change = max(pose_changes, default=0.0)
    if promoted:
        semantic_mode = "promote"
        pixel_relation = primary_video_hash != planned_video_hash
        pose_gate = (maximum_pose_change >= minimum_pose_change_degrees and
                     distinct_seconds >= minimum_distinct_seconds)
    else:
        semantic_mode = "abstain"
        pixel_relation = primary_video_hash == planned_video_hash
        pose_gate = True
    passed = all((trace_binding, encoder_equal, probe_equal, audio_equal,
                  pixel_relation, pose_gate))
    return {
        "schema_version": "aegis360.reaction-pre-review.v1",
        "passed": passed,
        "plan_mode": semantic_mode,
        "checks": {
            "trace_binding": trace_binding,
            "encoder_equal": encoder_equal,
            "decoded_stream_probe_equal": probe_equal,
            "decoded_audio_equal": audio_equal,
            "decoded_video_relation_correct": pixel_relation,
            "pose_and_duration_gate": pose_gate,
        },
        "differentiation": {
            "promoted_segment_count": len(promoted),
            "distinct_seconds": distinct_seconds,
            "maximum_pose_change_degrees": maximum_pose_change,
            "minimum_distinct_seconds": minimum_distinct_seconds,
            "minimum_pose_change_degrees": minimum_pose_change_degrees,
        },
        "human_visual_check_still_required": (
            "Mechanical differentiation does not establish editorial gain; "
            "inspect representative paired frames and motion before owner review."
        ),
    }
