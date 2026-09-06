"""Complete story segmentation from authorized typed continuous onsets."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid

SCHEMA = "aegis360.typed-story-segment-timeline.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")


def _finite(value: object) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def build_typed_story_segment_timeline(
    grid: Mapping[str, object], boundaries: Mapping[str, object], *,
    grid_sha256: str, boundaries_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (grid_sha256, boundaries_sha256)):
        raise ValueError("typed story timeline checksums are invalid")
    if (not isinstance(boundaries, Mapping)
            or set(boundaries) != {"schema_version", "source_id", "window",
                                  "inputs", "policy", "boundaries",
                                  "boundary_authority", "privacy", "limitations"}
            or boundaries.get("schema_version") !=
            "aegis360.typed-segment-boundaries.v1"
            or boundaries.get("source_id") != grid["source_id"]
            or boundaries.get("window") != grid["window"]
            or boundaries.get("inputs", {}).get("context_view_grid_sha256")
            != grid_sha256
            or set(boundaries.get("inputs", {})) != {
                "continuous_onset_candidates_sha256",
                "frame_difference_samples_sha256", "context_view_grid_sha256",
                "semantic_packet_sha256s", "semantic_evidence_sha256s",
                "boundary_policy_sha256"}
            or any(not isinstance(boundaries["inputs"].get(key), str)
                   or SHA256.fullmatch(boundaries["inputs"][key]) is None
                   for key in ("continuous_onset_candidates_sha256",
                               "frame_difference_samples_sha256",
                               "context_view_grid_sha256", "boundary_policy_sha256"))
            or any(not isinstance(boundaries["inputs"].get(key), list)
                   or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                          for value in boundaries["inputs"][key])
                   for key in ("semantic_packet_sha256s",
                               "semantic_evidence_sha256s"))
            or set(boundaries.get("policy", {})) != {
                "schema_version", "policy_id", "effective_timestamp_rule"}
            or boundaries["policy"].get("schema_version") !=
            "aegis360.typed-segment-boundary-policy.v1"
            or not isinstance(boundaries["policy"].get("policy_id"), str)
            or SAFE_ID.fullmatch(boundaries["policy"]["policy_id"]) is None
            or boundaries["policy"].get("effective_timestamp_rule") !=
            "first_sustained_high"
            or set(boundaries.get("boundary_authority", {})) != {
                "scope", "authorized_boundary_count", "artifact_validated",
                "candidate_selected", "renderer_command_emitted"}
            or boundaries.get("boundary_authority", {}).get("scope") !=
            "authorized_rows_only"
            or boundaries.get("boundary_authority", {}).get(
                "artifact_validated") is not True
            or boundaries.get("boundary_authority", {}).get(
                "candidate_selected") is not False
            or boundaries.get("boundary_authority", {}).get(
                "renderer_command_emitted") is not False
            or boundaries.get("privacy") != {
                "contains_source_path": False, "contains_pixels": False,
                "contains_identity": False, "contains_free_text": False}
            or not isinstance(boundaries.get("limitations"), list)
            or any(not isinstance(value, str)
                   for value in boundaries.get("limitations", []))):
        raise ValueError("typed story timeline lineage is invalid")
    window_start = float(grid["window"]["start_seconds"])
    window_end = window_start + float(grid["window"]["duration_seconds"])
    authorized = []
    seen_candidates = set()
    for row in boundaries.get("boundaries", []):
        if (not isinstance(row, Mapping) or set(row) != {
                "candidate_id", "disposition", "effective_timestamp_seconds",
                "uncertainty_interval", "support_interval", "typed_labels"}
                or row["candidate_id"] in seen_candidates
                or not isinstance(row["candidate_id"], str)
                or SAFE_ID.fullmatch(row["candidate_id"]) is None
                or row["disposition"] not in {
                    "authorized", "rejected", "abstained"}):
            raise ValueError("typed story boundary row is invalid")
        seen_candidates.add(row["candidate_id"])
        effective = row["effective_timestamp_seconds"]
        uncertainty = row["uncertainty_interval"]
        support = row["support_interval"]
        labels = row["typed_labels"]
        if (not isinstance(uncertainty, Mapping)
                or not isinstance(support, Mapping)
                or not isinstance(labels, Mapping)
                or set(labels) != {"classification", "structural_role",
                                   "change_type", "narrative_function",
                                   "viewer_value"}
                or set(uncertainty) != {"start_seconds", "end_seconds"}
                or set(support) != {"start_seconds", "end_seconds",
                                    "supporting_sample_count"}
                or any(not _finite(value) for value in (
                    uncertainty["start_seconds"], uncertainty["end_seconds"],
                    support["start_seconds"], support["end_seconds"]))
                or not uncertainty["start_seconds"] < uncertainty["end_seconds"]
                or uncertainty["end_seconds"] != support["start_seconds"]
                or support["end_seconds"] < support["start_seconds"]
                or not window_start <= uncertainty["start_seconds"]
                or support["end_seconds"] > window_end
                or isinstance(support["supporting_sample_count"], bool)
                or not isinstance(support["supporting_sample_count"], int)
                or support["supporting_sample_count"] < 2):
            raise ValueError("typed story boundary timing is invalid")
        if row["disposition"] == "authorized":
            if (not _finite(effective) or effective != uncertainty["end_seconds"]
                    or not window_start < effective < window_end
                    or labels["classification"] != "story_change"
                    or labels["structural_role"] not in {
                        "chapter_boundary", "within_chapter_cut", "ending_transition"}
                    or labels["change_type"] not in {
                        "gradual_transition", "motion_peak"}
                    or labels["narrative_function"] not in {
                        "establish_context", "action_continuation",
                        "activity_transition", "tension_build", "tension_release",
                        "closing"}
                    or labels["viewer_value"] not in {
                        "primary", "supporting", "low"}):
                raise ValueError("authorized typed boundary is outside the open window")
            authorized.append({
                "origin": "typed_continuous_onset",
                "candidate_id": row["candidate_id"],
                "effective_timestamp_seconds": float(effective),
                "typed_labels": dict(labels),
                "uncertainty_interval": dict(uncertainty),
                "support_interval": dict(support),
            })
        elif (effective is not None
              or (row["disposition"] == "rejected"
                  and labels["classification"] not in {
                      "capture_artifact", "no_semantic_change"})
              or (row["disposition"] == "abstained"
                  and labels["classification"] != "unknown")
              or any(labels[key] != "unknown" for key in (
                  "structural_role", "change_type", "narrative_function",
                  "viewer_value"))):
            raise ValueError("non-authorized typed boundary must remain null and unknown")
    times = [item["effective_timestamp_seconds"] for item in authorized]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("authorized typed boundaries must be ordered and unique")
    declared_count = boundaries["boundary_authority"].get(
        "authorized_boundary_count")
    if (isinstance(declared_count, bool) or not isinstance(declared_count, int)
            or declared_count != len(authorized)):
        raise ValueError("typed boundary authority count is inconsistent")

    points = [window_start, *times, window_end]
    segments = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        segments.append({
            "segment_id": f"segment:typed-story:{index:04d}",
            "start_seconds": float(start), "end_seconds": float(end),
            "left_boundary": None if index == 0 else dict(authorized[index - 1]),
            "right_boundary": (None if index == len(authorized)
                               else dict(authorized[index])),
        })
    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "inputs": {"context_view_grid_sha256": grid_sha256,
                   "typed_segment_boundaries_sha256": boundaries_sha256},
        "segments": segments,
        "planner_authority": {"candidate_selected": False,
                              "renderer_command_emitted": False},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_identity": False, "contains_free_text": False},
        "limitations": ["segmentation grants no camera or render authority",
                        "only authorized typed continuous onsets create boundaries"],
    }


def validate_typed_story_segment_timeline(
    document: Mapping[str, object], grid: Mapping[str, object],
    boundaries: Mapping[str, object], *, grid_sha256: str,
    boundaries_sha256: str,
) -> None:
    expected = build_typed_story_segment_timeline(
        grid, boundaries, grid_sha256=grid_sha256,
        boundaries_sha256=boundaries_sha256)
    if document != expected:
        raise ValueError("typed story segment timeline must exactly derive from inputs")
