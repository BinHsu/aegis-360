"""Symbolic bounded integration of story constraints and segment relevance."""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.bounded-story-segment-plan.v1"
POLICY_SCHEMA = "aegis360.bounded-story-segment-planner-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def plan_bounded_story_segments(
    segment_timeline: Mapping[str, object], constraints: Mapping[str, object],
    relevances: Sequence[Mapping[str, object]], grid: Mapping[str, object],
    policy: Mapping[str, object], *, start_seconds: float, end_seconds: float,
    segment_timeline_sha256: str, constraints_sha256: str,
    relevance_sha256s: Sequence[str], grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    required_policy = {"schema_version", "policy_id", "initial_candidate_id",
                       "unreviewed_behavior", "abstain_behavior",
                       "closing_behavior", "continuity_keep_relevance",
                       "switch_primary_visibility", "switch_primary_consistency"}
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA
            or policy["unreviewed_behavior"] != "retain_current"
            or policy["abstain_behavior"] != "retain_current"
            or policy["closing_behavior"] != "retain_current"
            or policy["continuity_keep_relevance"] != ["primary", "supporting"]
            or policy["switch_primary_visibility"] != ["clear", "partial"]
            or policy["switch_primary_consistency"] != "stable"):
        raise ValueError("bounded story planner policy is invalid")
    hashes = (segment_timeline_sha256, constraints_sha256, *relevance_sha256s,
              grid_sha256, policy_sha256)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in hashes):
        raise ValueError("bounded story planner checksums are invalid")
    if (segment_timeline.get("schema_version") != "aegis360.story-segment-timeline.v1"
            or constraints.get("schema_version") != "aegis360.story-planner-constraints.v1"
            or segment_timeline.get("source_id") != grid["source_id"]
            or constraints.get("source_id") != grid["source_id"]
            or len(relevances) != len(relevance_sha256s)):
        raise ValueError("bounded story planner lineage is invalid")
    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    if policy["initial_candidate_id"] not in candidate_ids:
        raise ValueError("bounded story planner initial candidate is undeclared")
    selected_segments = [item for item in segment_timeline["segments"]
                         if item["start_seconds"] >= start_seconds
                         and item["end_seconds"] <= end_seconds]
    if (not selected_segments or selected_segments[0]["start_seconds"] != start_seconds
            or selected_segments[-1]["end_seconds"] != end_seconds
            or any(left["end_seconds"] != right["start_seconds"]
                   for left, right in zip(selected_segments, selected_segments[1:]))):
        raise ValueError("bounded story planner window must align to contiguous segments")
    relevance_by_segment = {}
    for relevance in relevances:
        if (relevance.get("schema_version") != "aegis360.segment-view-relevance.v1"
                or relevance.get("source_id") != grid["source_id"]
                or relevance["segment_id"] in relevance_by_segment):
            raise ValueError("bounded story relevance is invalid")
        observations = relevance["evidence"]["candidate_observations"]
        if observations and [item["candidate_id"] for item in observations] != candidate_ids:
            raise ValueError("bounded story relevance candidate order is invalid")
        relevance_by_segment[relevance["segment_id"]] = relevance
    constraint_by_event = {item["event_id"]: item for item in constraints["constraints"]}
    current = policy["initial_candidate_id"]
    decisions = []
    for segment in selected_segments:
        left = segment["left_boundary"]
        constraint = None if left is None else constraint_by_event.get(left["event_id"])
        preference = ("continuity_preferred" if constraint is None
                      else constraint["transition_preference"])
        relevance = relevance_by_segment.get(segment["segment_id"])
        previous = current
        primary = None
        evidence_status = "unreviewed"
        reason = "unreviewed_retain_current"
        if relevance is not None:
            evidence_status = relevance["evidence"]["status"]
            if evidence_status == "abstain":
                reason = "abstain_retain_current"
            else:
                observations = {item["candidate_id"]: item
                                for item in relevance["evidence"]["candidate_observations"]}
                primary = next(item for item in observations.values()
                               if item["segment_relevance"] == "primary")
                primary_ok = (primary["visibility"] in policy["switch_primary_visibility"]
                              and primary["temporal_consistency"] ==
                              policy["switch_primary_consistency"])
                if preference == "closing_hold":
                    reason = "closing_hold_retain_current"
                elif preference == "change_permitted" and primary_ok:
                    current = primary["candidate_id"]
                    reason = "chapter_change_to_stable_primary"
                elif preference == "continuity_preferred":
                    current_observation = observations[current]
                    current_ok = (current_observation["segment_relevance"] in
                                  policy["continuity_keep_relevance"]
                                  and current_observation["visibility"] != "obstructed"
                                  and current_observation["temporal_consistency"] == "stable")
                    if current_ok:
                        reason = "continuity_keeps_usable_current"
                    elif primary_ok:
                        current = primary["candidate_id"]
                        reason = "continuity_current_unusable_switch_primary"
                    else:
                        reason = "no_safe_primary_retain_current"
                else:
                    raise ValueError("bounded story transition preference is unsupported")
        decisions.append({
            "segment_id": segment["segment_id"],
            "start_seconds": segment["start_seconds"],
            "end_seconds": segment["end_seconds"],
            "left_boundary_event_id": None if left is None else left["event_id"],
            "transition_preference": preference,
            "evidence_status": evidence_status,
            "previous_candidate_id": previous,
            "primary_candidate_id": None if primary is None else primary["candidate_id"],
            "selected_candidate_id": current, "reason": reason,
        })
    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "window": {"start_seconds": float(start_seconds),
                   "end_seconds": float(end_seconds)},
        "inputs": {"story_segment_timeline_sha256": segment_timeline_sha256,
                   "story_planner_constraints_sha256": constraints_sha256,
                   "segment_view_relevance_sha256s": list(relevance_sha256s),
                   "context_view_grid_sha256": grid_sha256,
                   "planner_policy_sha256": policy_sha256},
        "policy_id": policy["policy_id"], "decisions": decisions,
        "planner_authority": {"candidate_selected": True,
                              "numeric_costs_applied": False,
                              "renderer_command_emitted": False,
                              "production_eligible": False},
        "limitations": [
            "this is a bounded symbolic integration baseline, not the production global DP",
            "unreviewed and abstained segments retain the current candidate",
            "the plan cannot support source intervals outside its exact window",
        ],
    }


def validate_bounded_story_segment_plan(
    document: Mapping[str, object], segment_timeline: Mapping[str, object],
    constraints: Mapping[str, object], relevances: Sequence[Mapping[str, object]],
    grid: Mapping[str, object], policy: Mapping[str, object], *,
    segment_timeline_sha256: str, constraints_sha256: str,
    relevance_sha256s: Sequence[str], grid_sha256: str, policy_sha256: str,
) -> None:
    window = document.get("window", {})
    expected = plan_bounded_story_segments(
        segment_timeline, constraints, relevances, grid, policy,
        start_seconds=window.get("start_seconds", -1),
        end_seconds=window.get("end_seconds", -1),
        segment_timeline_sha256=segment_timeline_sha256,
        constraints_sha256=constraints_sha256,
        relevance_sha256s=relevance_sha256s, grid_sha256=grid_sha256,
        policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("bounded story segment plan must exactly derive from inputs")
