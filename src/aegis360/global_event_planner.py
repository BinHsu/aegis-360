"""Global DP over bounded event-level current/proposed view choices."""

from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .geometry import spherical_distance


def plan_global_events(
    utilities: Sequence[Mapping[str, object]],
    packets: Sequence[Mapping[str, object]],
    grid: Mapping[str, object], policy: Mapping[str, object],
    *, utility_sha256s: Sequence[str], packet_sha256s: Sequence[str],
    grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    required = {
        "schema_version", "policy_id", "minimum_advantage",
        "minimum_proposed_dwell_seconds", "switch_cost_each_way",
        "repeated_proposed_cost", "angular_cost_per_radian_each_way",
    }
    if not isinstance(policy, Mapping) or set(policy) != required or policy.get("schema_version") != "aegis360.global-event-planner-policy.v1":
        raise ValueError("global-event planner policy is invalid")
    numbers = [policy[key] for key in required - {"schema_version", "policy_id"}]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in numbers):
        raise ValueError("global-event planner costs must be finite and nonnegative")
    if not utilities or len(utilities) != len(packets):
        raise ValueError("global-event planner inputs must be nonempty and paired")
    if len(utility_sha256s) != len(utilities) or len(packet_sha256s) != len(packets) or any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in (*utility_sha256s, *packet_sha256s, grid_sha256, policy_sha256)
    ):
        raise ValueError("global-event planner checksums are invalid")

    geometry = {item["candidate_id"]: item for item in grid["candidates"]}
    nodes = []
    previous_end = -math.inf
    for utility, packet in zip(utilities, packets):
        if utility.get("schema_version") != "aegis360.event-candidate-utility.v1" or packet.get("schema_version") != "aegis360.event-review-packet.v1" or utility.get("source_id") != packet.get("source_id") or utility.get("event_id") != packet.get("event_id"):
            raise ValueError("global-event utility/packet lineage is invalid")
        start = packet["event_evidence"]["start_seconds"]
        end = packet["event_evidence"]["end_seconds"]
        if start < previous_end:
            raise ValueError("global events must be ordered and nonoverlapping")
        previous_end = end
        by_id = {item["candidate_id"]: item for item in utility["utilities"]}
        current_id = packet["event_evidence"]["current_candidate_id"]
        proposed_id = packet["event_evidence"]["proposed_candidate_id"]
        if set(by_id) != {current_id, proposed_id} or not by_id[current_id]["eligible"] or {current_id, proposed_id} - set(geometry):
            raise ValueError("global-event candidates are invalid")
        if utility["source_id"] != grid["source_id"]:
            raise ValueError("global-event grid source does not match")
        current_geometry = geometry[current_id]
        proposed_geometry = geometry[proposed_id]
        angular_distance = spherical_distance(
            (math.radians(current_geometry["yaw_degrees"]), math.radians(current_geometry["pitch_degrees"])),
            (math.radians(proposed_geometry["yaw_degrees"]), math.radians(proposed_geometry["pitch_degrees"])),
        )
        current_total = by_id[current_id]["total"]
        proposed_total = by_id[proposed_id]["total"]
        proposed_eligible = (
            by_id[proposed_id]["eligible"]
            and end - start >= policy["minimum_proposed_dwell_seconds"]
            and proposed_total >= current_total + policy["minimum_advantage"]
        )
        nodes.append({
            "event_id": utility["event_id"], "start_seconds": start,
            "end_seconds": end, "current_id": current_id,
            "proposed_id": proposed_id, "current_total": current_total,
            "proposed_total": proposed_total, "proposed_eligible": proposed_eligible,
            "angular_distance_radians": angular_distance,
        })

    states = {None: (0.0, [])}
    for node in nodes:
        next_states = {}
        choices = [(node["current_id"], node["current_total"], False)]
        if node["proposed_eligible"]:
            choices.append((node["proposed_id"], node["proposed_total"], True))
        for previous_proposed, (score, path) in states.items():
            for candidate_id, utility_total, is_proposed in choices:
                fixed_cost = 2.0 * policy["switch_cost_each_way"] if is_proposed else 0.0
                angular_cost = 2.0 * node["angular_distance_radians"] * policy["angular_cost_per_radian_each_way"] if is_proposed else 0.0
                repetition_cost = policy["repeated_proposed_cost"] if is_proposed and previous_proposed == candidate_id else 0.0
                cost = fixed_cost + angular_cost + repetition_cost
                total = score + utility_total - cost
                key = candidate_id if is_proposed else None
                candidate_path = path + [(candidate_id, utility_total, fixed_cost, angular_cost, repetition_cost, cost)]
                incumbent = next_states.get(key)
                if incumbent is None or total > incumbent[0] or (
                    total == incumbent[0] and tuple(item[0] for item in candidate_path) < tuple(item[0] for item in incumbent[1])
                ):
                    next_states[key] = (total, candidate_path)
        states = next_states
    objective, selected_path = min(
        states.values(), key=lambda item: (-item[0], tuple(row[0] for row in item[1])),
    )
    decisions = []
    for node, (candidate_id, utility_total, fixed_cost, angular_cost, repetition_cost, cost) in zip(nodes, selected_path):
        decisions.append({
            "event_id": node["event_id"], "start_seconds": node["start_seconds"],
            "end_seconds": node["end_seconds"], "selected_candidate_id": candidate_id,
            "selected_utility": utility_total,
            "planning_cost_components": {
                "fixed_two_way_switch": fixed_cost,
                "angular_two_way_transition": angular_cost,
                "repetition": repetition_cost,
            },
            "planning_cost": cost,
            "angular_distance_radians": node["angular_distance_radians"],
            "proposed_eligible": node["proposed_eligible"],
        })
    return {
        "schema_version": "aegis360.global-event-plan.v1",
        "planner": "event_dynamic_programming_v1",
        "inputs": {
            "event_candidate_utility_sha256s": list(utility_sha256s),
            "event_review_packet_sha256s": list(packet_sha256s),
            "context_view_grid_sha256": grid_sha256,
            "planner_policy_sha256": policy_sha256,
        },
        "policy": dict(policy), "objective": objective, "decisions": decisions,
        "limitations": [
            "v1 treats every proposed event shot as a bounded cut away and return",
            "camera angular motion and cross-event continuous paths are not yet modeled",
        ],
    }
