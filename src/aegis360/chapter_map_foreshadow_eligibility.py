"""Fail-closed structural eligibility for chapter-aware foreshadow planning."""

from __future__ import annotations

import re
from typing import Mapping

from .whole_film_chapter_map import validate_whole_film_chapter_map


SCHEMA = "aegis360.chapter-map-foreshadow-eligibility.v1"
QUALIFICATION_SCHEMA = "aegis360.chapter-map-qualification.v1"
POLICY_SCHEMA = "aegis360.chapter-map-foreshadow-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")


def assess_chapter_map_foreshadow_eligibility(
    chapter_map: Mapping[str, object], segment_timeline: Mapping[str, object],
    map_config: Mapping[str, object], qualification: Mapping[str, object],
    policy: Mapping[str, object], *, chapter_map_sha256: str,
    segment_timeline_sha256: str, map_config_sha256: str,
    qualification_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    validate_whole_film_chapter_map(
        chapter_map, segment_timeline, map_config,
        segment_timeline_sha256=segment_timeline_sha256,
        config_sha256=map_config_sha256,
    )
    hashes = (chapter_map_sha256, segment_timeline_sha256, map_config_sha256,
              qualification_sha256, policy_sha256)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in hashes):
        raise ValueError("chapter-map eligibility checksums are invalid")
    required_qualification = {"schema_version", "qualification_id",
                              "chapter_map_sha256", "status", "basis",
                              "evidence_sha256"}
    if (not isinstance(qualification, Mapping)
            or set(qualification) != required_qualification
            or qualification.get("schema_version") != QUALIFICATION_SCHEMA
            or not isinstance(qualification["qualification_id"], str)
            or SAFE_ID.fullmatch(qualification["qualification_id"]) is None
            or qualification["chapter_map_sha256"] != chapter_map_sha256
            or qualification["status"] not in {"qualified", "abstain"}
            or qualification["basis"] not in {"source_verified", "held_out_calibrated"}
            or SHA256.fullmatch(qualification["evidence_sha256"] or "") is None):
        raise ValueError("chapter-map qualification is invalid")
    required_policy = {"schema_version", "policy_id", "minimum_chapter_count",
                       "eligible_destination_roles", "ineligible_target_roles"}
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA
            or not isinstance(policy["policy_id"], str)
            or SAFE_ID.fullmatch(policy["policy_id"]) is None
            or policy["minimum_chapter_count"] != 2
            or policy["eligible_destination_roles"] != ["destination"]
            or policy["ineligible_target_roles"] != ["opening", "closing"]):
        raise ValueError("chapter-map foreshadow policy is invalid")

    reasons = []
    chapters = chapter_map["chapters"]
    if qualification["status"] != "qualified":
        reasons.append("chapter_map_not_independently_qualified")
    if len(chapters) < policy["minimum_chapter_count"]:
        reasons.append("insufficient_chapter_count")
    destinations = [item for item in chapters
                    if item["chapter_role"] in policy["eligible_destination_roles"]]
    if not destinations:
        reasons.append("no_destination_chapter")
    elif all(item == chapters[0] or item["chapter_role"] in policy["ineligible_target_roles"]
             for item in destinations):
        reasons.append("no_later_eligible_destination")
    return {
        "schema_version": SCHEMA, "source_id": chapter_map["source_id"],
        "inputs": {"whole_film_chapter_map_sha256": chapter_map_sha256,
                   "chapter_map_qualification_sha256": qualification_sha256,
                   "foreshadow_policy_sha256": policy_sha256},
        "policy_id": policy["policy_id"],
        "qualification_id": qualification["qualification_id"],
        "eligible": not reasons, "reasons": reasons,
        "planner_authority": {"may_plan_one_prefix_foreshadow": not reasons,
                              "teaser_interval_selected": False,
                              "candidate_selected": False,
                              "renderer_command_emitted": False},
        "limitations": [
            "eligibility does not select a teaser interval, view or transition",
            "source verification is benchmark evidence, not a product dependency",
            "the chronological body and retained payoff remain ADR 0011 requirements",
        ],
    }
