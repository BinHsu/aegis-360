"""Closed blind-review observations and joined structural replication gate."""

from __future__ import annotations

import math
import re
from typing import Mapping, Sequence


REVIEW_SCHEMA = "aegis360.structural-chapter-blind-review.v1"
EVALUATION_SCHEMA = "aegis360.structural-chapter-blind-evaluation.v1"
SCHEDULE_CONFIG_SHA256 = "3964162f0cb99bf9959cee1b19bef9fd041a04a76dfae9085052c9babb30d8ba"
SCORE_CONTRACT_SHA256 = "7f8b05656986030715f226f9c9c33fc375e1afe3e361fc37b54651851a8aa5cd"
SELECTION_PROOF_SHA256 = "ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID = re.compile(r"^packet-[0-9a-f]{20}$")
REVIEWER_SLOT = re.compile(r"^reviewer-[0-9a-f]{20}$")
SAFE_EVENT_ID = re.compile(r"^event:multi:[0-9]{4}$")
SAFE_SIGNAL_ID = re.compile(r"^event:scene-change:[0-9]{4}$")
RESPONSE_KEYS = {"packet_id", "early_persistence", "late_persistence",
                 "persistent_difference", "transition_support",
                 "artifact_evidence", "classification"}
PRIVACY = {"contains_principal_identity": False, "contains_source_identity": False,
           "contains_time": False, "contains_signal": False, "contains_score": False,
           "contains_peer_result": False, "contains_path": False,
           "contains_pixels": False, "contains_free_text": False}
REVIEW_AUTHORITY = {"blind_observation": True, "semantic_boundary": False,
                    "camera": False, "render": False}
EVALUATION_AUTHORITY = {"replication_evidence": True, "semantic_boundary": False,
                        "camera": False, "render": False}


def _sha(value: object) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _packet_ids(values: Sequence[str]) -> list[str]:
    if (not isinstance(values, Sequence) or isinstance(values, (str, bytes))
            or len(values) != 8 or any(not isinstance(value, str)
            or PACKET_ID.fullmatch(value) is None for value in values)
            or len(set(values)) != 8):
        raise ValueError("public packet IDs must be eight unique opaque IDs")
    return list(values)


def _expected_classification(response: Mapping[str, object]) -> str:
    if response["artifact_evidence"] == "present":
        return "capture_artifact"
    if (response["early_persistence"] == "observed"
            and response["late_persistence"] == "observed"
            and response["persistent_difference"] == "persistent"
            and response["transition_support"] != "contradicts"
            and response["artifact_evidence"] == "absent"):
        return "story_change"
    if (response["persistent_difference"] == "not_persistent"
            and response["artifact_evidence"] == "absent"
            and response["early_persistence"] != "unclear"
            and response["late_persistence"] != "unclear"):
        return "no_semantic_change"
    return "abstain"


def _validate_responses(responses: object, packet_ids: Sequence[str]) -> list[dict]:
    if not isinstance(responses, list) or len(responses) != 8:
        raise ValueError("blind review requires exactly eight responses")
    enums = {
        "early_persistence": {"observed", "not_observed", "unclear"},
        "late_persistence": {"observed", "not_observed", "unclear"},
        "persistent_difference": {"persistent", "not_persistent", "unclear"},
        "transition_support": {"supports", "contradicts", "insufficient"},
        "artifact_evidence": {"present", "absent", "unclear"},
        "classification": {"story_change", "capture_artifact",
                           "no_semantic_change", "abstain"},
    }
    normalized = []
    for expected_packet, response in zip(packet_ids, responses):
        if (not isinstance(response, Mapping) or set(response) != RESPONSE_KEYS
                or response.get("packet_id") != expected_packet
                or any(response.get(field) not in allowed
                       for field, allowed in enums.items())
                or response.get("classification") != _expected_classification(response)):
            raise ValueError("blind review response is malformed or inconsistent")
        normalized.append(dict(response))
    return normalized


def build_structural_blind_review(
    *, public_packet_ids: Sequence[str], public_index_sha256: str,
    bundle_tree_sha256: str, schedule_config_sha256: str,
    reviewer_slot_id: str, responses: object,
) -> dict[str, object]:
    packet_ids = _packet_ids(public_packet_ids)
    if (not _sha(public_index_sha256) or not _sha(bundle_tree_sha256)
            or schedule_config_sha256 != SCHEDULE_CONFIG_SHA256
            or not isinstance(reviewer_slot_id, str)
            or REVIEWER_SLOT.fullmatch(reviewer_slot_id) is None):
        raise ValueError("blind review lineage or reviewer slot is invalid")
    return {
        "schema_version": REVIEW_SCHEMA,
        "reviewer_slot_id": reviewer_slot_id,
        "inputs": {"public_index_sha256": public_index_sha256,
                   "bundle_tree_sha256": bundle_tree_sha256,
                   "schedule_config_sha256": schedule_config_sha256},
        "responses": _validate_responses(responses, packet_ids),
        "privacy": dict(PRIVACY),
        "authority": dict(REVIEW_AUTHORITY),
    }


def validate_structural_blind_review(
    document: Mapping[str, object], *, public_packet_ids: Sequence[str],
    public_index_sha256: str, bundle_tree_sha256: str,
    schedule_config_sha256: str,
) -> None:
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "reviewer_slot_id", "inputs",
                                 "responses", "privacy", "authority"}):
        raise ValueError("blind review artifact is not closed")
    expected = build_structural_blind_review(
        public_packet_ids=public_packet_ids,
        public_index_sha256=public_index_sha256,
        bundle_tree_sha256=bundle_tree_sha256,
        schedule_config_sha256=schedule_config_sha256,
        reviewer_slot_id=document.get("reviewer_slot_id"),
        responses=document.get("responses"))
    if document != expected:
        raise ValueError("blind review artifact must exactly derive from inputs")


def _validate_mapping_and_scores(private_mapping: object, structural_scores: object,
                                 packet_ids: Sequence[str]) -> dict[str, float]:
    if (not isinstance(private_mapping, list) or len(private_mapping) != 8
            or not isinstance(structural_scores, list) or len(structural_scores) != 8):
        raise ValueError("joined evaluation requires the complete frozen eight")
    mapping_keys = {"packet_id", "selection_rank", "event_id", "signal_id"}
    score_keys = {"selection_rank", "event_id", "signal_id", "score"}
    identities = []
    packet_to_identity = {}
    for packet, row in zip(packet_ids, private_mapping):
        if (not isinstance(row, Mapping) or set(row) != mapping_keys
                or row.get("packet_id") != packet
                or type(row.get("selection_rank")) is not int
                or not 1 <= row["selection_rank"] <= 8
                or not isinstance(row.get("event_id"), str)
                or SAFE_EVENT_ID.fullmatch(row["event_id"]) is None
                or not isinstance(row.get("signal_id"), str)
                or SAFE_SIGNAL_ID.fullmatch(row["signal_id"]) is None):
            raise ValueError("private packet mapping is malformed")
        identity = (row["selection_rank"], row["event_id"], row["signal_id"])
        identities.append(identity)
        packet_to_identity[packet] = identity
    if len(set(identities)) != 8 or {item[0] for item in identities} != set(range(1, 9)):
        raise ValueError("private packet mapping is incomplete or duplicated")
    score_by_identity = {}
    for row in structural_scores:
        if (not isinstance(row, Mapping) or set(row) != score_keys
                or type(row.get("selection_rank")) is not int
                or not isinstance(row.get("event_id"), str)
                or not isinstance(row.get("signal_id"), str)
                or isinstance(row.get("score"), bool)
                or not isinstance(row.get("score"), (int, float))
                or not math.isfinite(row["score"]) or not 0 <= row["score"] <= 1):
            raise ValueError("structural score row is malformed")
        identity = (row["selection_rank"], row["event_id"], row["signal_id"])
        if identity in score_by_identity:
            raise ValueError("structural score identity is duplicated")
        score_by_identity[identity] = float(row["score"])
    if set(score_by_identity) != set(identities):
        raise ValueError("structural scores do not exactly match proof-selected packets")
    return {packet: score_by_identity[identity]
            for packet, identity in packet_to_identity.items()}


def evaluate_structural_blind_reviews(
    *, public_packet_ids: Sequence[str], public_index_sha256: str,
    bundle_tree_sha256: str, schedule_config_sha256: str,
    private_mapping: object, private_mapping_sha256: str,
    structural_scores: object, structural_scores_sha256: str,
    selection_proof_sha256: str, score_contract_sha256: str,
    review_a: Mapping[str, object], review_a_sha256: str,
    review_b: Mapping[str, object], review_b_sha256: str,
) -> dict[str, object]:
    packet_ids = _packet_ids(public_packet_ids)
    hashes = (public_index_sha256, bundle_tree_sha256, private_mapping_sha256,
              structural_scores_sha256, review_a_sha256, review_b_sha256)
    if (not all(_sha(value) for value in hashes)
            or schedule_config_sha256 != SCHEDULE_CONFIG_SHA256
            or selection_proof_sha256 != SELECTION_PROOF_SHA256
            or score_contract_sha256 != SCORE_CONTRACT_SHA256
            or review_a_sha256 == review_b_sha256):
        raise ValueError("joined evaluation lineage is invalid")
    for review in (review_a, review_b):
        validate_structural_blind_review(
            review, public_packet_ids=packet_ids,
            public_index_sha256=public_index_sha256,
            bundle_tree_sha256=bundle_tree_sha256,
            schedule_config_sha256=schedule_config_sha256)
    if review_a["reviewer_slot_id"] == review_b["reviewer_slot_id"]:
        raise ValueError("blind reviews require two distinct opaque reviewer slots")
    scores = _validate_mapping_and_scores(private_mapping, structural_scores, packet_ids)
    paired = []
    has_nonbinary = False
    has_disagreement = False
    for packet, left, right in zip(packet_ids, review_a["responses"], review_b["responses"]):
        left_class, right_class = left["classification"], right["classification"]
        unanimous = left_class if left_class == right_class else None
        has_disagreement |= unanimous is None
        has_nonbinary |= unanimous in {"capture_artifact", "abstain"}
        paired.append({"packet_id": packet, "review_a": left_class,
                       "review_b": right_class, "unanimous_class": unanimous,
                       "structural_score": scores[packet]})
    story = [row["structural_score"] for row in paired
             if row["unanimous_class"] == "story_change"]
    no_change = [row["structural_score"] for row in paired
                 if row["unanimous_class"] == "no_semantic_change"]
    if has_disagreement:
        outcome, reason, adequate = "inconclusive", "reviewer_disagreement", False
    elif has_nonbinary:
        outcome, reason, adequate = "inconclusive", "artifact_or_abstain", False
    elif len(story) < 2 or len(no_change) < 2:
        outcome, reason, adequate = "inconclusive", "class_imbalance", False
    else:
        adequate = True
        if min(story) > max(no_change):
            outcome, reason = "replicated", "strict_score_ordering_passed"
        else:
            outcome, reason = "reject", "strict_score_ordering_failed"
    return {
        "schema_version": EVALUATION_SCHEMA,
        "inputs": {"public_index_sha256": public_index_sha256,
                   "bundle_tree_sha256": bundle_tree_sha256,
                   "schedule_config_sha256": schedule_config_sha256,
                   "selection_proof_sha256": selection_proof_sha256,
                   "score_contract_sha256": score_contract_sha256,
                   "private_mapping_sha256": private_mapping_sha256,
                   "structural_scores_sha256": structural_scores_sha256,
                   "review_a_sha256": review_a_sha256,
                   "review_b_sha256": review_b_sha256},
        "packet_results": paired,
        "gate": {"outcome": outcome, "reason": reason,
                 "adequate_for_ordering": adequate,
                 "unanimous_story_change_count": len(story),
                 "unanimous_no_semantic_change_count": len(no_change),
                 "minimum_story_score": min(story) if adequate else None,
                 "maximum_no_semantic_change_score": max(no_change) if adequate else None,
                 "strict_ordering_passed": outcome == "replicated" if adequate else None,
                 "no_backfill": True},
        "authority": dict(EVALUATION_AUTHORITY),
        "limitations": [
            "replication is within-source evidence and does not calibrate a threshold",
            "distinct opaque slots require a coordinator-private distinct-principal attestation",
            "no packet may be omitted, replaced or backfilled",
        ],
    }


def validate_structural_blind_evaluation(
    document: Mapping[str, object], **evaluation_inputs: object,
) -> None:
    """Reject any evaluation artifact that is not the exact derived result."""
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "inputs", "packet_results",
                                 "gate", "authority", "limitations"}):
        raise ValueError("joined evaluation artifact is not closed")
    expected = evaluate_structural_blind_reviews(**evaluation_inputs)
    if document != expected:
        raise ValueError("joined evaluation artifact must exactly derive from inputs")
