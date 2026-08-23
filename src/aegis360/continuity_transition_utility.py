"""Deterministic transition utilities from closed continuity evidence."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.continuity-transition-utility.v1"
POLICY_SCHEMA = "aegis360.continuity-transition-utility-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def _endpoint_key(assessability: str, cue_match: str) -> str:
    key = (assessability, cue_match)
    mapping = {("clear", "present"): "clear_present",
               ("partial", "present"): "partial_present",
               ("clear", "absent"): "clear_absent"}
    if key not in mapping:
        raise ValueError("continuity endpoint combination is invalid")
    return mapping[key]


def build_continuity_transition_utility(
    evidence: Mapping[str, object], grid: Mapping[str, object],
    policy: Mapping[str, object], *, evidence_sha256: str,
    grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (evidence_sha256, grid_sha256, policy_sha256)):
        raise ValueError("continuity-transition utility checksums are invalid")
    if (evidence.get("schema_version") != "aegis360.causal-continuity-evidence.v1"
            or evidence.get("source_id") != grid.get("source_id")
            or evidence.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256):
        raise ValueError("continuity-transition utility lineage is invalid")
    required_policy = {"schema_version", "policy_id", "endpoint_weights",
                       "preservation_weights"}
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA
            or set(policy.get("endpoint_weights", {})) != {
                "clear_present", "partial_present", "clear_absent"}
            or set(policy.get("preservation_weights", {})) != {
                "preserves", "partial", "breaks"}):
        raise ValueError("continuity-transition utility policy is invalid")
    values = [*policy["endpoint_weights"].values(),
              *policy["preservation_weights"].values()]
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) for value in values):
        raise ValueError("continuity-transition utility weights are invalid")
    endpoint = policy["endpoint_weights"]
    preservation = policy["preservation_weights"]
    if not (endpoint["clear_present"] >= endpoint["partial_present"]
            > endpoint["clear_absent"]
            and preservation["preserves"] >= preservation["partial"]
            > preservation["breaks"]):
        raise ValueError("continuity-transition weights invert evidence meaning")

    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    edge_utilities = []
    for edge in evidence.get("edges", []):
        status = edge.get("status")
        observations = edge.get("candidate_observations")
        if status == "abstain":
            if observations != []:
                raise ValueError("abstained continuity edge cannot carry observations")
            by_id = {}
        elif status == "observed":
            if (not isinstance(observations, list)
                    or [item.get("candidate_id") for item in observations
                        if isinstance(item, Mapping)] != candidate_ids):
                raise ValueError("continuity observations must match grid order")
            by_id = {item["candidate_id"]: item for item in observations}
        else:
            raise ValueError("continuity edge status is invalid")
        transitions = []
        for previous in candidate_ids:
            for following in candidate_ids:
                components = {"from_cue_support": 0.0, "to_cue_support": 0.0,
                              "same_candidate_preservation": 0.0}
                if status == "observed":
                    before = by_id[previous]
                    after = by_id[following]
                    components["from_cue_support"] = float(endpoint[_endpoint_key(
                        before["from_assessability"], before["from_cue_match"])])
                    components["to_cue_support"] = float(endpoint[_endpoint_key(
                        after["to_assessability"], after["to_cue_match"])])
                    if previous == following:
                        components["same_candidate_preservation"] = float(
                            preservation[before["relationship_preservation"]])
                transitions.append({"previous_candidate_id": previous,
                                    "next_candidate_id": following,
                                    "components": components,
                                    "total": float(sum(components.values()))})
        edge_utilities.append({"from_segment_id": edge["from_segment_id"],
                               "to_segment_id": edge["to_segment_id"],
                               "evidence_status": status,
                               "transitions": transitions})
    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "inputs": {"causal_continuity_evidence_sha256": evidence_sha256,
                   "context_view_grid_sha256": grid_sha256,
                   "continuity_transition_utility_policy_sha256": policy_sha256},
        "policy_id": policy["policy_id"], "edge_utilities": edge_utilities,
        "planner_authority": {"candidate_selected": False,
                              "transition_selected": False,
                              "transition_costs_applied": False,
                              "renderer_command_emitted": False},
        "limitations": ["weights are tunable hypotheses, not calibrated preference",
                        "cross-candidate cells use endpoint cues, not unobserved preservation"],
    }


def validate_continuity_transition_utility(
    document: Mapping[str, object], evidence: Mapping[str, object],
    grid: Mapping[str, object], policy: Mapping[str, object], *,
    evidence_sha256: str, grid_sha256: str, policy_sha256: str,
) -> None:
    expected = build_continuity_transition_utility(
        evidence, grid, policy, evidence_sha256=evidence_sha256,
        grid_sha256=grid_sha256, policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("continuity transition utility must exactly derive from inputs")
