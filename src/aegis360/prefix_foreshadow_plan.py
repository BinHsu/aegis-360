"""Plan one bounded future prefix followed by the complete chronological body."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.prefix-foreshadow-plan.v1"
PROPOSAL_SCHEMA = "aegis360.prefix-foreshadow-proposal.v1"
POLICY_SCHEMA = "aegis360.prefix-foreshadow-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def plan_prefix_foreshadow(
    chapter_map: Mapping[str, object], eligibility: Mapping[str, object],
    proposal: Mapping[str, object], policy: Mapping[str, object], *,
    chapter_map_sha256: str, eligibility_sha256: str,
    proposal_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    if any(SHA256.fullmatch(value or "") is None for value in (
        chapter_map_sha256, eligibility_sha256, proposal_sha256, policy_sha256,
    )):
        raise ValueError("prefix foreshadow checksums are invalid")
    if (chapter_map.get("schema_version") != "aegis360.whole-film-chapter-map.v1"
            or eligibility.get("schema_version") !=
            "aegis360.chapter-map-foreshadow-eligibility.v1"
            or eligibility.get("source_id") != chapter_map.get("source_id")
            or eligibility.get("inputs", {}).get("whole_film_chapter_map_sha256") !=
            chapter_map_sha256
            or eligibility.get("eligible") is not True
            or eligibility.get("planner_authority", {}).get(
                "may_plan_one_prefix_foreshadow") is not True):
        raise ValueError("prefix foreshadow eligibility is invalid")
    required_proposal = {"schema_version", "proposal_id", "target_chapter_id",
                         "start_seconds", "end_seconds", "evidence_sha256"}
    if (not isinstance(proposal, Mapping) or set(proposal) != required_proposal
            or proposal.get("schema_version") != PROPOSAL_SCHEMA
            or SHA256.fullmatch(proposal.get("evidence_sha256") or "") is None):
        raise ValueError("prefix foreshadow proposal is invalid")
    expected_policy = {
        "schema_version": POLICY_SCHEMA,
        "policy_id": "single-source-synchronous-prefix-v1",
        "minimum_duration_seconds": 1.0,
        "maximum_duration_seconds": 3.0,
        "maximum_prefix_count": 1,
        "body_behavior": "complete_chronological",
        "payoff_behavior": "retain_in_body",
        "audio_behavior": "source_synchronous",
    }
    if policy != expected_policy:
        raise ValueError("prefix foreshadow policy is invalid")
    matches = [item for item in chapter_map["chapters"]
               if item["chapter_id"] == proposal["target_chapter_id"]]
    if len(matches) != 1 or matches[0]["chapter_role"] != "destination":
        raise ValueError("prefix target must be one declared destination chapter")
    target = matches[0]
    start = proposal["start_seconds"]
    end = proposal["end_seconds"]
    if (not isinstance(start, (int, float)) or isinstance(start, bool)
            or not isinstance(end, (int, float)) or isinstance(end, bool)
            or start < target["start_seconds"] or end > target["end_seconds"]
            or not policy["minimum_duration_seconds"] <= end - start <=
            policy["maximum_duration_seconds"]):
        raise ValueError("prefix interval is outside the bounded destination")
    window = chapter_map["window"]
    body_start = float(window["start_seconds"])
    body_end = body_start + float(window["duration_seconds"])
    return {
        "schema_version": SCHEMA, "source_id": chapter_map["source_id"],
        "inputs": {"whole_film_chapter_map_sha256": chapter_map_sha256,
                   "chapter_map_eligibility_sha256": eligibility_sha256,
                   "prefix_proposal_sha256": proposal_sha256,
                   "prefix_policy_sha256": policy_sha256},
        "policy_id": policy["policy_id"],
        "temporal_structure": "prefix_foreshadow",
        "spans": [
            {"sequence_index": 0, "role": "future_prefix_copy",
             "source_start_seconds": float(start), "source_end_seconds": float(end),
             "target_chapter_id": target["chapter_id"]},
            {"sequence_index": 1, "role": "complete_chronological_body",
             "source_start_seconds": body_start, "source_end_seconds": body_end,
             "target_chapter_id": None},
        ],
        "invariants": {"prefix_count": 1, "body_source_time_monotonic": True,
                       "body_complete": True, "payoff_retained": True,
                       "audio_behavior": policy["audio_behavior"]},
        "planner_authority": {"temporal_spans_selected": True,
                              "candidate_selected": False,
                              "camera_geometry_selected": False,
                              "renderer_command_emitted": False},
    }


def validate_prefix_foreshadow_plan(
    document: Mapping[str, object], chapter_map: Mapping[str, object],
    eligibility: Mapping[str, object], proposal: Mapping[str, object],
    policy: Mapping[str, object], *, chapter_map_sha256: str,
    eligibility_sha256: str, proposal_sha256: str, policy_sha256: str,
) -> None:
    expected = plan_prefix_foreshadow(
        chapter_map, eligibility, proposal, policy,
        chapter_map_sha256=chapter_map_sha256,
        eligibility_sha256=eligibility_sha256, proposal_sha256=proposal_sha256,
        policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("prefix foreshadow plan must exactly derive from inputs")
