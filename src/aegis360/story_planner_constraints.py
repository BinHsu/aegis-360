"""Deterministic candidate-free planner constraints from ordered story evidence."""

from __future__ import annotations

import re
from typing import Mapping, Sequence


SCHEMA = "aegis360.story-planner-constraints.v1"
POLICY_SCHEMA = "aegis360.story-planner-constraint-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def build_story_planner_constraints(
    semantics: Sequence[Mapping[str, object]],
    packets: Sequence[Mapping[str, object]], policy: Mapping[str, object], *,
    semantics_sha256s: Sequence[str], packet_sha256s: Sequence[str],
    policy_sha256: str,
) -> dict[str, object]:
    required_policy = {"schema_version", "policy_id", "structural_rules",
                       "viewer_priority"}
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA):
        raise ValueError("story constraint policy is invalid")
    expected_roles = {"chapter_boundary", "within_chapter_cut", "ending_transition"}
    expected_rules = {
        "chapter_boundary": {"transition_preference": "change_permitted",
                             "repetition_memory": "reset"},
        "within_chapter_cut": {"transition_preference": "continuity_preferred",
                               "repetition_memory": "retain"},
        "ending_transition": {"transition_preference": "closing_hold",
                              "repetition_memory": "retain"},
    }
    if policy["structural_rules"] != expected_rules:
        raise ValueError("story structural rules must retain the v1 safe mapping")
    if (not isinstance(policy["viewer_priority"], Mapping)
            or set(policy["viewer_priority"]) != {"primary", "supporting", "low"}
            or set(policy["viewer_priority"].values()) != {"high", "medium", "low"}):
        raise ValueError("story viewer-priority mapping is invalid")
    if (not semantics or len(semantics) != len(packets)
            or len(semantics_sha256s) != len(semantics)
            or len(packet_sha256s) != len(packets)
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in (*semantics_sha256s, *packet_sha256s, policy_sha256))):
        raise ValueError("story constraint inputs/checksums are invalid")
    constraints = []
    previous_start = float("-inf")
    source_id = packets[0].get("source_id")
    for evidence, packet, evidence_sha, packet_sha in zip(
        semantics, packets, semantics_sha256s, packet_sha256s, strict=True,
    ):
        if (evidence.get("schema_version") != "aegis360.scene-story-semantics.v1"
                or packet.get("schema_version") != "aegis360.scene-story-review-packet.v1"
                or evidence.get("source_id") != source_id
                or packet.get("source_id") != source_id
                or evidence.get("event_id") != packet.get("event_id")
                or evidence.get("inputs", {}).get("scene_story_review_packet_sha256") != packet_sha):
            raise ValueError("story constraint lineage is invalid")
        start = packet["event"]["start_seconds"]
        if start < previous_start:
            raise ValueError("story constraint events must be chronological")
        previous_start = start
        observed = evidence["evidence"]
        if observed["status"] != "observed" or observed["structural_role"] not in expected_roles:
            raise ValueError("story constraint v1 requires observed benchmark evidence")
        role = observed["structural_role"]
        constraints.append({
            "event_id": packet["event_id"], "start_seconds": start,
            "end_seconds": packet["event"]["end_seconds"],
            "structural_role": role,
            "narrative_function": observed["narrative_function"],
            "change_type": observed["change_type"],
            "viewer_value": observed["viewer_value"],
            "transition_preference": policy["structural_rules"][role]["transition_preference"],
            "repetition_memory": policy["structural_rules"][role]["repetition_memory"],
            "coverage_priority": policy["viewer_priority"][observed["viewer_value"]],
        })
    return {
        "schema_version": SCHEMA, "source_id": source_id,
        "inputs": {"scene_story_semantics_sha256s": list(semantics_sha256s),
                   "scene_story_review_packet_sha256s": list(packet_sha256s),
                   "constraint_policy_sha256": policy_sha256},
        "policy_id": policy["policy_id"], "constraints": constraints,
        "planner_authority": {"candidate_selected": False,
                              "numeric_costs_applied": False,
                              "renderer_command_emitted": False},
        "limitations": [
            "symbolic constraints require independent candidate-view relevance",
            "v1 does not convert preferences to numeric planner costs",
            "benchmark labels do not make human review a product dependency",
        ],
    }
