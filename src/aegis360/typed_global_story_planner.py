"""Numeric persistent-view DP for typed story-segment timelines."""

from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .geometry import spherical_distance

SCHEMA = "aegis360.typed-global-story-plan.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
ROLE_PREFERENCE = {"chapter_boundary": "change_permitted",
                   "within_chapter_cut": "continuity_preferred",
                   "ending_transition": "closing_hold"}


def build_typed_global_story_plan(
    timeline: Mapping[str, object], utilities: Sequence[Mapping[str, object]],
    continuity: Mapping[str, object], grid: Mapping[str, object],
    policy: Mapping[str, object], *, timeline_sha256: str,
    utility_sha256s: Sequence[str], continuity_sha256: str,
    grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    hashes = (timeline_sha256, *utility_sha256s, continuity_sha256,
              grid_sha256, policy_sha256)
    if (len(utilities) != len(utility_sha256s)
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in hashes)):
        raise ValueError("typed global planner checksums are invalid")
    if (not isinstance(timeline, Mapping) or set(timeline) != {
            "schema_version", "source_id", "window", "inputs", "segments",
            "planner_authority", "privacy", "limitations"}
            or timeline.get("schema_version") != "aegis360.typed-story-segment-timeline.v1"
            or timeline.get("source_id") != grid["source_id"]
            or timeline.get("window") != grid["window"]
            or not isinstance(timeline.get("inputs"), Mapping)
            or set(timeline["inputs"]) != {"context_view_grid_sha256",
                                           "typed_segment_boundaries_sha256"}
            or timeline["inputs"].get("context_view_grid_sha256") != grid_sha256
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in timeline["inputs"].values())
            or timeline.get("planner_authority") != {
                "candidate_selected": False, "renderer_command_emitted": False}
            or timeline.get("privacy") != {
                "contains_source_path": False, "contains_pixels": False,
                "contains_identity": False, "contains_free_text": False}
            or not isinstance(timeline.get("limitations"), list)
            or any(not isinstance(value, str) for value in timeline["limitations"])):
        raise ValueError("typed global planner timeline lineage is invalid")
    required_policy = {"schema_version", "policy_id", "initial_candidate_id",
                       "minimum_advantage", "minimum_dwell_seconds",
                       "switch_cost", "angular_cost_per_radian"}
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") !=
            "aegis360.global-story-segment-planner-policy.v1"
            or not isinstance(policy.get("policy_id"), str)
            or SAFE_ID.fullmatch(policy["policy_id"]) is None
            or not isinstance(policy.get("initial_candidate_id"), str)
            or SAFE_ID.fullmatch(policy["initial_candidate_id"]) is None):
        raise ValueError("typed global planner policy is invalid")
    for key in ("minimum_advantage", "minimum_dwell_seconds", "switch_cost",
                "angular_cost_per_radian"):
        value = policy[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError("typed global planner numeric policy is invalid")
    geometry = {item["candidate_id"]: item for item in grid["candidates"]}
    initial = policy["initial_candidate_id"]
    if initial not in geometry:
        raise ValueError("typed global planner initial candidate is undeclared")
    segments = timeline.get("segments", [])
    if (not isinstance(segments, list) or not segments
            or any(not isinstance(item, Mapping) or set(item) != {
                "segment_id", "start_seconds", "end_seconds", "left_boundary",
                "right_boundary"} for item in segments)
            or any(not isinstance(item, Mapping) for item in utilities)
            or [item.get("segment_id") for item in utilities]
            != [item.get("segment_id") for item in segments]):
        raise ValueError("typed global utilities must cover segments in order")
    for segment in segments:
        if (not isinstance(segment.get("segment_id"), str)
                or SAFE_ID.fullmatch(segment["segment_id"]) is None
                or any(isinstance(segment.get(key), bool)
                       or not isinstance(segment.get(key), (int, float))
                       or not math.isfinite(segment[key])
                       for key in ("start_seconds", "end_seconds"))
                or segment["end_seconds"] <= segment["start_seconds"]):
            raise ValueError("typed global timeline segment is invalid")
        for boundary in (segment["left_boundary"], segment["right_boundary"]):
            if boundary is None:
                continue
            if (not isinstance(boundary, Mapping)
                    or set(boundary) != {"origin", "candidate_id",
                                         "effective_timestamp_seconds",
                                         "typed_labels", "uncertainty_interval",
                                         "support_interval"}
                    or boundary.get("origin") != "typed_continuous_onset"
                    or not isinstance(boundary.get("typed_labels"), Mapping)
                    or set(boundary["typed_labels"]) != {
                        "classification", "structural_role", "change_type",
                        "narrative_function", "viewer_value"}):
                raise ValueError("typed global timeline boundary is invalid")
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    if (segments[0].get("start_seconds") != window_start
            or segments[-1].get("end_seconds") != window_end
            or len({item.get("segment_id") for item in segments}) != len(segments)
            or any(left.get("end_seconds") != right.get("start_seconds")
                   or left.get("right_boundary") != right.get("left_boundary")
                   for left, right in zip(segments, segments[1:]))
            or segments[0].get("left_boundary") is not None
            or segments[-1].get("right_boundary") is not None):
        raise ValueError("typed global timeline must cover the complete window")
    utility_by_segment = {}
    candidate_ids = list(geometry)
    for utility in utilities:
        rows = utility.get("utilities")
        if (set(utility) != {"schema_version", "source_id", "segment_id", "inputs",
                             "policy_id", "evidence_status", "utilities",
                             "planner_authority", "limitations"}
                or utility.get("schema_version") != "aegis360.segment-candidate-utility.v1"
                or utility.get("source_id") != grid["source_id"]
                or utility.get("evidence_status") not in {"observed", "abstain"}
                or not isinstance(utility.get("inputs"), Mapping)
                or set(utility["inputs"]) != {"segment_view_relevance_sha256",
                                               "context_view_grid_sha256",
                                               "utility_policy_sha256"}
                or utility["inputs"].get("context_view_grid_sha256") != grid_sha256
                or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                       for value in utility["inputs"].values())
                or not isinstance(utility.get("policy_id"), str)
                or SAFE_ID.fullmatch(utility["policy_id"]) is None
                or utility.get("planner_authority") != {
                    "candidate_selected": False, "transition_costs_applied": False,
                    "minimum_dwell_applied": False}
                or not isinstance(utility.get("limitations"), list)
                or any(not isinstance(value, str) for value in utility["limitations"])
                or not isinstance(rows, list)
                or any(not isinstance(row, Mapping) for row in rows)
                or [row.get("candidate_id") for row in rows] != candidate_ids):
            raise ValueError("typed global segment utility is invalid")
        for row in rows:
            components, total = row.get("components"), row.get("total")
            if (set(row) != {"candidate_id", "eligible", "components", "total"}
                    or not isinstance(row["eligible"], bool)
                    or not isinstance(components, Mapping)
                    or set(components) != {"segment_relevance", "visibility",
                                           "temporal_consistency"}
                    or any(isinstance(value, bool) or not isinstance(value, (int, float))
                           or not math.isfinite(value) for value in components.values())
                    or isinstance(total, bool) or not isinstance(total, (int, float))
                    or not math.isfinite(total)
                    or not math.isclose(total, sum(components.values()),
                                        rel_tol=0, abs_tol=1e-12)):
                raise ValueError("typed global segment utility row is invalid")
        if ((utility["evidence_status"] == "abstain" and any(
                row["eligible"] or row["total"] != 0 for row in rows))
                or (utility["evidence_status"] == "observed" and any(
                    not row["eligible"] for row in rows))):
            raise ValueError("typed global abstention must expose no alternative")
        utility_by_segment[utility["segment_id"]] = utility

    if (not isinstance(continuity, Mapping) or set(continuity) != {
            "schema_version", "source_id", "inputs", "policy_id",
            "edge_utilities", "planner_authority", "limitations"}
            or continuity.get("schema_version") !=
            "aegis360.continuity-transition-utility.v1"
            or continuity.get("source_id") != grid["source_id"]
            or not isinstance(continuity.get("inputs"), Mapping)
            or set(continuity["inputs"]) != {"causal_continuity_evidence_sha256",
                                              "context_view_grid_sha256",
                                              "continuity_transition_utility_policy_sha256"}
            or continuity["inputs"].get("context_view_grid_sha256") != grid_sha256
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in continuity["inputs"].values())
            or not isinstance(continuity.get("policy_id"), str)
            or SAFE_ID.fullmatch(continuity["policy_id"]) is None
            or continuity.get("planner_authority") != {
                "candidate_selected": False, "transition_selected": False,
                "transition_costs_applied": False, "renderer_command_emitted": False}
            or not isinstance(continuity.get("limitations"), list)
            or any(not isinstance(value, str) for value in continuity["limitations"])):
        raise ValueError("typed global continuity lineage is invalid")
    expected_edges = [(left["segment_id"], right["segment_id"])
                      for left, right in zip(segments, segments[1:])]
    edges = continuity.get("edge_utilities")
    if (not isinstance(edges, list)
            or any(not isinstance(edge, Mapping) or set(edge) != {
                "from_segment_id", "to_segment_id", "evidence_status",
                "transitions"} for edge in edges)
            or [(edge.get("from_segment_id"), edge.get("to_segment_id"))
                for edge in edges] != expected_edges):
        raise ValueError("typed global continuity edges must cover adjacency")
    expected_pairs = [(left, right) for left in candidate_ids for right in candidate_ids]
    edge_by_to = {}
    for edge in edges:
        transitions = edge.get("transitions")
        if (edge.get("evidence_status") not in {"observed", "abstain"}
                or not isinstance(transitions, list)
                or any(not isinstance(row, Mapping) for row in transitions)
                or [(row.get("previous_candidate_id"), row.get("next_candidate_id"))
                    for row in transitions] != expected_pairs):
            raise ValueError("typed global continuity matrix is invalid")
        matrix = {}
        for row in transitions:
            components, total = row.get("components"), row.get("total")
            if (set(row) != {"previous_candidate_id", "next_candidate_id",
                             "components", "total"}
                    or not isinstance(components, Mapping)
                    or set(components) != {"from_cue_support", "to_cue_support",
                                           "same_candidate_preservation"}
                    or any(isinstance(value, bool) or not isinstance(value, (int, float))
                           or not math.isfinite(value) for value in components.values())
                    or isinstance(total, bool) or not isinstance(total, (int, float))
                    or not math.isfinite(total)
                    or not math.isclose(total, sum(components.values()),
                                        rel_tol=0, abs_tol=1e-12)):
                raise ValueError("typed global continuity row is invalid")
            matrix[(row["previous_candidate_id"], row["next_candidate_id"])] = float(total)
        if edge["evidence_status"] == "abstain" and any(matrix.values()):
            raise ValueError("typed global abstained edge must be neutral")
        edge_by_to[edge["to_segment_id"]] = (edge["evidence_status"], matrix)

    states = {initial: (0.0, [])}
    for index, segment in enumerate(segments):
        utility = utility_by_segment[segment["segment_id"]]
        totals = {} if utility["evidence_status"] == "abstain" else {
            row["candidate_id"]: float(row["total"])
            for row in utility["utilities"] if row["eligible"]}
        boundary = segment.get("left_boundary")
        preference = ("no_constraint" if boundary is None else
                      ROLE_PREFERENCE.get(boundary.get("typed_labels", {}).get(
                          "structural_role")))
        if preference is None:
            raise ValueError("typed boundary structural role is unsupported")
        edge = None if index == 0 else edge_by_to[segment["segment_id"]]
        next_states = {}
        for previous, (score, path) in states.items():
            retain_edge = 0.0 if edge is None else edge[1][(previous, previous)]
            retain_value = totals.get(previous, 0.0) + retain_edge
            choices = [previous]
            duration = segment["end_seconds"] - segment["start_seconds"]
            if (totals and preference != "closing_hold"
                    and duration >= policy["minimum_dwell_seconds"]):
                choices += [candidate for candidate in totals if candidate != previous
                            and totals[candidate] + (0.0 if edge is None else edge[1][(previous, candidate)])
                            >= retain_value + policy["minimum_advantage"]]
            for candidate in choices:
                changed = candidate != previous
                edge_value = 0.0 if edge is None else edge[1][(previous, candidate)]
                angle = 0.0
                if changed:
                    before, after = geometry[previous], geometry[candidate]
                    angle = spherical_distance(
                        (math.radians(before["yaw_degrees"]), math.radians(before["pitch_degrees"])),
                        (math.radians(after["yaw_degrees"]), math.radians(after["pitch_degrees"])))
                fixed = float(policy["switch_cost"]) if changed else 0.0
                angular = angle * policy["angular_cost_per_radian"] if changed else 0.0
                segment_value = totals.get(candidate, 0.0)
                objective = score + segment_value + edge_value - fixed - angular
                row = {"segment_id": segment["segment_id"],
                       "start_seconds": float(segment["start_seconds"]),
                       "end_seconds": float(segment["end_seconds"]),
                       "previous_candidate_id": previous,
                       "selected_candidate_id": candidate,
                       "evidence_status": utility["evidence_status"],
                       "continuity_evidence_status": None if edge is None else edge[0],
                       "transition_preference": preference,
                       "selected_utility": segment_value,
                       "selected_transition_utility": edge_value,
                       "planning_cost_components": {"fixed_switch": fixed,
                                                    "angular_transition": angular},
                       "planning_cost": fixed + angular,
                       "angular_distance_radians": angle}
                candidate_path = path + [row]
                incumbent = next_states.get(candidate)
                key = tuple(item["selected_candidate_id"] for item in candidate_path)
                if incumbent is None or objective > incumbent[0] or (
                        objective == incumbent[0] and key < tuple(
                            item["selected_candidate_id"] for item in incumbent[1])):
                    next_states[candidate] = (objective, candidate_path)
        states = next_states
    objective, decisions = min(states.values(), key=lambda item: (
        -item[0], tuple(row["selected_candidate_id"] for row in item[1])))
    return {"schema_version": SCHEMA, "source_id": grid["source_id"],
            "window": dict(grid["window"]),
            "inputs": {"typed_story_segment_timeline_sha256": timeline_sha256,
                       "segment_candidate_utility_sha256s": list(utility_sha256s),
                       "continuity_transition_utility_sha256": continuity_sha256,
                       "context_view_grid_sha256": grid_sha256,
                       "planner_policy_sha256": policy_sha256},
            "policy_id": policy["policy_id"], "objective": objective,
            "decisions": decisions,
            "planner_authority": {"candidate_selected": True,
                                  "numeric_costs_applied": True,
                                  "continuity_utility_applied": True,
                                  "renderer_command_emitted": False,
                                  "production_eligible": not any(
                                      item["evidence_status"] == "abstain"
                                      for item in utilities)
                                  and not any(edge["evidence_status"] == "abstain"
                                              for edge in edges)},
            "limitations": [
                "chapter and within-chapter labels share the same numeric switch gate in v1",
                "minimum dwell is the destination segment duration, not accumulated dwell",
                "minimum advantage is a pre-cost local pruning rule",
                "camera rendering remains a separate authority"]}


def validate_typed_global_story_plan(document: Mapping[str, object], *args, **kwargs) -> None:
    if document != build_typed_global_story_plan(*args, **kwargs):
        raise ValueError("typed global story plan must exactly derive from inputs")
