"""Persistent-view global DP for complete story-segment timelines."""

from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .geometry import spherical_distance


SCHEMA = "aegis360.global-story-segment-plan.v1"
UTILITY_SCHEMA = "aegis360.segment-candidate-utility.v1"
POLICY_SCHEMA = "aegis360.global-story-segment-planner-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def plan_global_story_segments(
    timeline: Mapping[str, object], constraints: Mapping[str, object],
    utilities: Sequence[Mapping[str, object]], grid: Mapping[str, object],
    policy: Mapping[str, object], *, timeline_sha256: str,
    constraints_sha256: str, utility_sha256s: Sequence[str],
    grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    """Select a persistent candidate for every segment with numeric costs.

    Every segment requires an exact utility artifact. An explicit abstention
    exposes only the incoming candidate and manufactures no alternative.
    """
    validate_context_view_grid(grid)
    hashes = (timeline_sha256, constraints_sha256, *utility_sha256s,
              grid_sha256, policy_sha256)
    if (len(utilities) != len(utility_sha256s)
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in hashes)):
        raise ValueError("global-story planner checksums are invalid")
    required_policy = {
        "schema_version", "policy_id", "initial_candidate_id",
        "minimum_advantage", "minimum_dwell_seconds", "switch_cost",
        "angular_cost_per_radian",
    }
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA):
        raise ValueError("global-story planner policy is invalid")
    for key in ("minimum_advantage", "minimum_dwell_seconds", "switch_cost",
                "angular_cost_per_radian"):
        value = policy[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError("global-story planner costs must be finite and nonnegative")
    if (timeline.get("schema_version") != "aegis360.story-segment-timeline.v1"
            or constraints.get("schema_version") != "aegis360.story-planner-constraints.v1"
            or timeline.get("source_id") != grid["source_id"]
            or constraints.get("source_id") != grid["source_id"]):
        raise ValueError("global-story planner lineage is invalid")

    candidate_geometry = {item["candidate_id"]: item for item in grid["candidates"]}
    initial = policy["initial_candidate_id"]
    if initial not in candidate_geometry:
        raise ValueError("global-story initial candidate is undeclared")
    segments = timeline.get("segments", [])
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    if (not segments or segments[0]["start_seconds"] != window_start
            or segments[-1]["end_seconds"] != window_end
            or any(left["end_seconds"] != right["start_seconds"]
                   for left, right in zip(segments, segments[1:]))
            or len({item["segment_id"] for item in segments}) != len(segments)):
        raise ValueError("global-story timeline must cover the complete grid window")
    if ([item.get("segment_id") for item in utilities]
            != [item["segment_id"] for item in segments]):
        raise ValueError("global-story utilities must cover segments in order")

    utility_by_segment = {}
    for utility in utilities:
        segment_id = utility.get("segment_id")
        if (utility.get("schema_version") != UTILITY_SCHEMA
                or utility.get("source_id") != grid["source_id"]
                or segment_id in utility_by_segment
                or segment_id not in {item["segment_id"] for item in segments}
                or utility.get("evidence_status") not in {"observed", "abstain"}
                or utility.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256):
            raise ValueError("global-story utility lineage is invalid")
        rows = utility.get("utilities")
        if (not isinstance(rows, list)
                or [row.get("candidate_id") for row in rows] != list(candidate_geometry)):
            raise ValueError("story utility must cover grid candidates in order")
        for row in rows:
            total = row.get("total")
            components = row.get("components")
            if (set(row) != {"candidate_id", "eligible", "components", "total"}
                    or not isinstance(row["eligible"], bool)
                    or not isinstance(components, Mapping)
                    or set(components) != {"segment_relevance", "visibility",
                                           "temporal_consistency"}
                    or any(isinstance(value, bool)
                           or not isinstance(value, (int, float))
                           or not math.isfinite(value)
                           for value in components.values())
                    or isinstance(total, bool) or not isinstance(total, (int, float))
                    or not math.isfinite(total)
                    or not math.isclose(total, sum(components.values()),
                                        rel_tol=0, abs_tol=1e-12)):
                raise ValueError("global-story utility row is invalid")
        if utility["evidence_status"] == "abstain" and any(
                row["eligible"] or row["total"] != 0 for row in rows):
            raise ValueError("abstained story utility must expose no alternative")
        utility_by_segment[segment_id] = utility

    constraint_by_event = {}
    for constraint in constraints.get("constraints", []):
        event_id = constraint.get("event_id")
        if (event_id in constraint_by_event
                or constraint.get("transition_preference") not in {
                    "continuity_preferred", "change_permitted", "closing_hold",
                }):
            raise ValueError("global-story constraint is invalid")
        constraint_by_event[event_id] = constraint
    boundary_event_ids = {
        boundary["event_id"]
        for segment in segments
        for boundary in (segment.get("left_boundary"), segment.get("right_boundary"))
        if boundary is not None
    }
    if set(constraint_by_event) != boundary_event_ids:
        raise ValueError("global-story constraints must cover timeline boundaries exactly")

    states = {initial: (0.0, [])}
    for segment in segments:
        utility = utility_by_segment[segment["segment_id"]]
        totals = {} if utility["evidence_status"] == "abstain" else {
            row["candidate_id"]: float(row["total"])
            for row in utility["utilities"] if row["eligible"]
        }
        left = segment.get("left_boundary")
        constraint = None if left is None else constraint_by_event.get(left.get("event_id"))
        preference = "continuity_preferred" if constraint is None else constraint["transition_preference"]
        next_states = {}
        for previous, (score, path) in states.items():
            previous_utility = totals.get(previous, 0.0)
            choices = [previous]
            duration = segment["end_seconds"] - segment["start_seconds"]
            if (totals and preference != "closing_hold"
                    and duration >= policy["minimum_dwell_seconds"]):
                choices.extend(candidate for candidate in totals
                               if candidate != previous
                               and totals[candidate] >= previous_utility + policy["minimum_advantage"])
            for candidate in choices:
                changed = candidate != previous
                angular_distance = 0.0
                if changed:
                    before = candidate_geometry[previous]
                    after = candidate_geometry[candidate]
                    angular_distance = spherical_distance(
                        (math.radians(before["yaw_degrees"]), math.radians(before["pitch_degrees"])),
                        (math.radians(after["yaw_degrees"]), math.radians(after["pitch_degrees"])),
                    )
                fixed_cost = float(policy["switch_cost"]) if changed else 0.0
                angular_cost = (angular_distance * policy["angular_cost_per_radian"]
                                if changed else 0.0)
                utility_total = totals.get(candidate, 0.0)
                total = score + utility_total - fixed_cost - angular_cost
                row = {
                    "segment_id": segment["segment_id"],
                    "start_seconds": float(segment["start_seconds"]),
                    "end_seconds": float(segment["end_seconds"]),
                    "previous_candidate_id": previous,
                    "selected_candidate_id": candidate,
                    "evidence_status": utility["evidence_status"],
                    "transition_preference": preference,
                    "selected_utility": utility_total,
                    "planning_cost_components": {
                        "fixed_switch": fixed_cost,
                        "angular_transition": angular_cost,
                    },
                    "planning_cost": fixed_cost + angular_cost,
                    "angular_distance_radians": angular_distance,
                }
                candidate_path = path + [row]
                incumbent = next_states.get(candidate)
                path_key = tuple(item["selected_candidate_id"] for item in candidate_path)
                if (incumbent is None or total > incumbent[0] or (
                        total == incumbent[0] and path_key < tuple(
                            item["selected_candidate_id"] for item in incumbent[1]))):
                    next_states[candidate] = (total, candidate_path)
        states = next_states
    objective, decisions = min(
        states.values(),
        key=lambda item: (-item[0], tuple(row["selected_candidate_id"] for row in item[1])),
    )
    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "inputs": {
            "story_segment_timeline_sha256": timeline_sha256,
            "story_planner_constraints_sha256": constraints_sha256,
            "segment_candidate_utility_sha256s": list(utility_sha256s),
            "context_view_grid_sha256": grid_sha256,
            "planner_policy_sha256": policy_sha256,
        },
        "policy_id": policy["policy_id"], "objective": objective,
        "decisions": decisions,
        "planner_authority": {
            "candidate_selected": True, "numeric_costs_applied": True,
            "renderer_command_emitted": False, "production_eligible": True,
        },
        "limitations": [
            "v1 permits a new view only at a declared story-segment boundary",
            "abstained segment utility retains the incoming candidate",
        ],
    }


def validate_global_story_segment_plan(
    document: Mapping[str, object], timeline: Mapping[str, object],
    constraints: Mapping[str, object], utilities: Sequence[Mapping[str, object]],
    grid: Mapping[str, object], policy: Mapping[str, object], *,
    timeline_sha256: str, constraints_sha256: str,
    utility_sha256s: Sequence[str], grid_sha256: str, policy_sha256: str,
) -> None:
    expected = plan_global_story_segments(
        timeline, constraints, utilities, grid, policy,
        timeline_sha256=timeline_sha256,
        constraints_sha256=constraints_sha256,
        utility_sha256s=utility_sha256s,
        grid_sha256=grid_sha256,
        policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("global story segment plan must exactly derive from inputs")
