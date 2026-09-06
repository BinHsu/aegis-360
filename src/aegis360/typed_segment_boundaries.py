"""Deterministic typed boundaries from reviewed continuous-onset candidates."""

from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

from .continuous_onset_semantic_packet import validate_continuous_onset_semantic_packet
from .continuous_onset_semantic_evidence import validate_continuous_onset_semantic_evidence
from .context_views import validate_context_view_grid

SCHEMA = "aegis360.typed-segment-boundaries.v1"
POLICY_SCHEMA = "aegis360.typed-segment-boundary-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")


def build_typed_segment_boundaries(
    onset: Mapping[str, object], samples: Mapping[str, object],
    grid: Mapping[str, object], packets: Sequence[Mapping[str, object]],
    evidences: Sequence[Mapping[str, object]], policy: Mapping[str, object], *,
    onset_sha256: str, samples_sha256: str, grid_sha256: str,
    packet_sha256s: Sequence[str], evidence_sha256s: Sequence[str],
    policy_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    hashes = (onset_sha256, samples_sha256, grid_sha256, *packet_sha256s,
              *evidence_sha256s, policy_sha256)
    if (len(packets) != len(packet_sha256s)
            or len(evidences) != len(evidence_sha256s)
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in hashes)):
        raise ValueError("typed-boundary checksums are invalid")
    if (not isinstance(policy, Mapping) or set(policy) != {
            "schema_version", "policy_id", "effective_timestamp_rule"}
            or policy.get("schema_version") != POLICY_SCHEMA
            or not isinstance(policy.get("policy_id"), str)
            or SAFE_ID.fullmatch(policy["policy_id"]) is None
            or policy.get("effective_timestamp_rule") != "first_sustained_high"):
        raise ValueError("typed-boundary policy is invalid")
    if (onset.get("schema_version") != "aegis360.continuous-onset-candidates.v1"
            or onset.get("source_id") != samples.get("source_id")
            or onset.get("source_id") != grid.get("source_id")
            or onset.get("window") != samples.get("window")
            or onset.get("window") != grid.get("window")
            or onset.get("inputs", {}).get("frame_difference_samples_sha256")
            != samples_sha256):
        raise ValueError("typed-boundary source lineage is invalid")
    candidates = onset.get("candidates", [])
    candidate_ids = [item.get("candidate_id") for item in candidates]
    if (len(candidate_ids) != len(set(candidate_ids))
            or [item.get("candidate_id") for item in packets] != candidate_ids
            or [item.get("candidate_id") for item in evidences] != candidate_ids):
        raise ValueError("typed-boundary review inputs must cover candidates in order")
    sample_by_time = {item["pts_seconds"]: item for item in samples.get("samples", [])}
    rows = []
    for candidate, packet, evidence, packet_sha in zip(
            candidates, packets, evidences, packet_sha256s):
        validate_continuous_onset_semantic_packet(
            packet, onset, samples, grid, onset_sha256=onset_sha256,
            samples_sha256=samples_sha256, grid_sha256=grid_sha256)
        provenance = evidence.get("provenance", {})
        semantic = evidence.get("evidence", {})
        reconstructed_config = {
            "schema_version": "aegis360.continuous-onset-semantic-evidence-config.v1",
            "reviewer_type": provenance.get("reviewer_type"),
            "reviewer_id": provenance.get("reviewer_id"),
            "reviewer_asset_sha256": provenance.get("reviewer_asset_sha256"),
            "status": semantic.get("status"),
            "classification": semantic.get("classification"),
            "structural_role": semantic.get("structural_role"),
            "change_type": semantic.get("change_type"),
            "narrative_function": semantic.get("narrative_function"),
            "viewer_value": semantic.get("viewer_value"),
        }
        validate_continuous_onset_semantic_evidence(
            evidence, reconstructed_config, packet,
            config_sha256=evidence.get("inputs", {}).get("review_config_sha256", ""),
            packet_sha256=packet_sha,
        )
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "source_id", "candidate_id", "inputs",
                "provenance", "evidence", "planner_authority", "privacy",
                "limitations"}
                or evidence.get("schema_version") !=
                "aegis360.continuous-onset-semantic-evidence.v1"
                or evidence.get("source_id") != onset["source_id"]
                or evidence.get("inputs", {}).get(
                    "continuous_onset_semantic_packet_sha256") != packet_sha
                or evidence.get("evidence", {}).get("hard_cut_claimed") is not False
                or evidence.get("planner_authority", {}).get(
                    "story_boundary_emitted") is not False
                or set(evidence.get("evidence", {})) != {
                    "status", "classification", "structural_role", "change_type",
                    "narrative_function", "viewer_value", "hard_cut_claimed"}
                or set(evidence.get("privacy", {})) != {
                    "contains_timestamp", "contains_view", "contains_confidence",
                    "contains_free_text", "contains_identity"}
                or any(value is not False for value in evidence["privacy"].values())):
            raise ValueError("typed-boundary semantic evidence lineage is invalid")
        semantic = evidence["evidence"]
        status = semantic.get("status")
        classification = semantic.get("classification")
        labels = (semantic.get("structural_role"), semantic.get("change_type"),
                  semantic.get("narrative_function"), semantic.get("viewer_value"))
        effective = None
        if status == "abstain" and classification == "unknown" and labels == ("unknown",) * 4:
            disposition = "abstained"
        elif status == "observed" and classification in {
                "capture_artifact", "no_semantic_change"} and labels == ("unknown",) * 4:
            disposition = "rejected"
        elif (status == "observed" and classification == "story_change"
              and semantic.get("structural_role") in {
                  "chapter_boundary", "within_chapter_cut", "ending_transition"}
              and semantic.get("change_type") in {"gradual_transition", "motion_peak"}
              and semantic.get("narrative_function") in {
                  "establish_context", "action_continuation",
                  "activity_transition", "tension_build", "tension_release",
                  "closing"}
              and semantic.get("viewer_value") in {"primary", "supporting", "low"}):
            disposition = "authorized"
            effective = candidate["uncertainty_interval"]["end_seconds"]
            upper_rows = [item for item in packet["samples"]
                          if item["temporal_role"] == "upper_bound"]
            support_start = candidate["support_interval"]["start_seconds"]
            source_row = sample_by_time.get(effective)
            high = onset["policy"]["high_threshold"]
            if (len(upper_rows) != 1 or effective != support_start
                    or upper_rows[0]["timestamp_seconds"] != effective
                    or source_row is None
                    or not math.isclose(source_row["normalized_difference"],
                                        upper_rows[0]["normalized_difference"],
                                        rel_tol=0, abs_tol=1e-12)
                    or source_row["normalized_difference"] < high):
                raise ValueError("authorized boundary is not first sustained high")
        else:
            raise ValueError("typed-boundary semantic disposition is invalid")
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "disposition": disposition,
            "effective_timestamp_seconds": effective,
            "uncertainty_interval": dict(candidate["uncertainty_interval"]),
            "support_interval": dict(candidate["support_interval"]),
            "typed_labels": {"classification": classification,
                             "structural_role": labels[0],
                             "change_type": labels[1],
                             "narrative_function": labels[2],
                             "viewer_value": labels[3]},
        })
    return {
        "schema_version": SCHEMA, "source_id": onset["source_id"],
        "window": dict(onset["window"]),
        "inputs": {"continuous_onset_candidates_sha256": onset_sha256,
                   "frame_difference_samples_sha256": samples_sha256,
                   "context_view_grid_sha256": grid_sha256,
                   "semantic_packet_sha256s": list(packet_sha256s),
                   "semantic_evidence_sha256s": list(evidence_sha256s),
                   "boundary_policy_sha256": policy_sha256},
        "policy": dict(policy), "boundaries": rows,
        "boundary_authority": {
            "scope": "authorized_rows_only",
            "authorized_boundary_count": sum(row["disposition"] == "authorized"
                                               for row in rows),
            "artifact_validated": True,
            "candidate_selected": False, "renderer_command_emitted": False},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_identity": False, "contains_free_text": False},
        "limitations": ["boundary authority does not grant camera or render authority"],
    }


def validate_typed_segment_boundaries(document: Mapping[str, object], *args, **kwargs) -> None:
    if document != build_typed_segment_boundaries(*args, **kwargs):
        raise ValueError("typed segment boundaries must exactly derive from inputs")
