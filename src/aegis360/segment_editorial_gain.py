"""Closed benchmark label for relative editorial gain of one segment edit."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.segment-editorial-gain.v1"
CONFIG_SCHEMA = "aegis360.segment-editorial-gain-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
REASONS = {"stronger_causal_cues", "smoother_transition", "no_preference_gain",
           "abrupt_switch", "clearer_subject", "clearer_context"}


def build_segment_editorial_gain(config: Mapping[str, object], *, config_sha256: str) -> dict[str, object]:
    required = {"schema_version", "review_id", "reviewer_type", "reviewer_id",
                "reviewer_asset_sha256", "candidate_media_sha256",
                "baseline_media_sha256", "decision", "reasons"}
    if (not isinstance(config, Mapping) or set(config) != required
            or config.get("schema_version") != CONFIG_SCHEMA
            or SHA256.fullmatch(config_sha256 or "") is None):
        raise ValueError("segment editorial-gain config is invalid")
    if any(not isinstance(config[key], str) or SAFE_ID.fullmatch(config[key]) is None
           for key in ("review_id", "reviewer_id")):
        raise ValueError("segment editorial-gain IDs are invalid")
    if config["reviewer_type"] not in {"human", "agent", "local_model"}:
        raise ValueError("segment editorial-gain reviewer type is invalid")
    asset_sha = config["reviewer_asset_sha256"]
    if config["reviewer_type"] == "local_model":
        if not isinstance(asset_sha, str) or SHA256.fullmatch(asset_sha) is None:
            raise ValueError("local reviewer requires an exact asset checksum")
    elif asset_sha is not None:
        raise ValueError("human or agent reviewer cannot claim a model asset")
    candidate_sha = config["candidate_media_sha256"]
    baseline_sha = config["baseline_media_sha256"]
    if (not isinstance(candidate_sha, str) or SHA256.fullmatch(candidate_sha) is None
            or not isinstance(baseline_sha, str) or SHA256.fullmatch(baseline_sha) is None
            or candidate_sha == baseline_sha):
        raise ValueError("segment editorial-gain media lineage is invalid")
    reasons = config["reasons"]
    if (not isinstance(reasons, list) or not reasons or len(reasons) != len(set(reasons))
            or any(reason not in REASONS for reason in reasons)):
        raise ValueError("segment editorial-gain reasons are invalid")
    decision = config["decision"]
    if decision == "retain_baseline":
        if "no_preference_gain" not in reasons:
            raise ValueError("baseline retention requires no-preference-gain evidence")
    elif decision == "promote_candidate":
        if "no_preference_gain" in reasons or "abrupt_switch" in reasons:
            raise ValueError("candidate promotion contradicts the declared reasons")
    else:
        raise ValueError("segment editorial-gain decision is invalid")
    return {
        "schema_version": SCHEMA,
        "input": {"review_config_sha256": config_sha256},
        "review_id": config["review_id"],
        "media": {"candidate_sha256": candidate_sha, "baseline_sha256": baseline_sha},
        "provenance": {"reviewer_type": config["reviewer_type"],
                       "reviewer_id": config["reviewer_id"],
                       "reviewer_asset_sha256": asset_sha},
        "decision": decision, "reasons": list(reasons),
        "planner_mapping": {"candidate_eligible": decision == "promote_candidate",
                            "fallback": ("candidate" if decision == "promote_candidate"
                                         else "baseline")},
        "limitations": ["human labels are benchmark evidence, not a product dependency",
                        "one pairwise response does not establish population preference"],
    }


def validate_segment_editorial_gain(
    document: Mapping[str, object], config: Mapping[str, object], *, config_sha256: str,
) -> None:
    if document != build_segment_editorial_gain(config, config_sha256=config_sha256):
        raise ValueError("segment editorial gain must exactly derive from config")
