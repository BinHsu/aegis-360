"""Label-free structural scores for exactly eight proof-selected centers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from fractions import Fraction
from typing import Mapping

from .structural_chapter_labeled_contrast import evaluation_metrics


SCHEMA = "aegis360.structural-chapter-label-free-scores.v1"
PROOF_SCHEMA = "aegis360.structural-chapter-blind-selection-proof.v1"
PROOF_SHA256 = "ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567"
CONTRACT_SHA256 = "7f8b05656986030715f226f9c9c33fc375e1afe3e361fc37b54651851a8aa5cd"
SOURCE_SHA256 = "4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc"
SHA = re.compile(r"^[0-9a-f]{64}$")
PRIVACY = {"contains_semantic_label": False, "contains_expected_class": False,
           "contains_source_path": False}
AUTHORITY = {"structural_score": True, "semantic_boundary": False,
             "camera": False, "render": False}


def canonical_contract_bytes(contract: Mapping[str, object]) -> bytes:
    return json.dumps(contract, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def validate_score_contract(contract: Mapping[str, object]) -> None:
    if (not isinstance(contract, Mapping)
            or set(contract) != {"acquisition", "descriptor",
                                 "sample_offsets_seconds", "score"}
            or hashlib.sha256(canonical_contract_bytes(contract)).hexdigest()
               != CONTRACT_SHA256):
        raise ValueError("structural score contract is invalid")


def _fraction(value: object) -> Fraction:
    if (not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}
            or type(value.get("numerator")) is not int
            or type(value.get("denominator")) is not int
            or value["denominator"] <= 0):
        raise ValueError("proof-selected center is invalid")
    result = Fraction(value["numerator"], value["denominator"])
    if result.numerator != value["numerator"] or result.denominator != value["denominator"]:
        raise ValueError("proof-selected center must be reduced")
    return result


def selected_centers(proof: Mapping[str, object]):
    if (not isinstance(proof, Mapping) or proof.get("schema_version") != PROOF_SCHEMA
            or set(proof) != {"schema_version", "source_id", "inputs",
                              "selection_policy", "universe", "selected",
                              "authority", "privacy", "limitations"}
            or not isinstance(proof.get("selected"), list)
            or len(proof["selected"]) != 8):
        raise ValueError("selection proof is invalid for label-free scoring")
    rows = []; identities = set()
    for rank, row in enumerate(proof["selected"], start=1):
        if (not isinstance(row, Mapping)
                or set(row) != {"selection_rank", "event_id", "signal_id",
                                "source_time", "packet_sha256", "selection_digest"}
                or row.get("selection_rank") != rank
                or not all(isinstance(row.get(k), str) for k in
                           ("event_id", "signal_id", "packet_sha256", "selection_digest"))
                or SHA.fullmatch(row["packet_sha256"]) is None
                or SHA.fullmatch(row["selection_digest"]) is None):
            raise ValueError("selection proof row is invalid")
        identity = (row["event_id"], row["signal_id"])
        if identity in identities:
            raise ValueError("selection proof identity is duplicated")
        identities.add(identity); rows.append((row, _fraction(row["source_time"])))
    universe = {(row.get("event_id"), row.get("signal_id")): row
                for row in proof.get("universe", []) if isinstance(row, Mapping)}
    if len(proof.get("universe", [])) != 26:
        raise ValueError("selection proof universe is invalid")
    for row, _ in rows:
        source = universe.get((row["event_id"], row["signal_id"]))
        if source is None or source.get("disposition") != "selected" or any(
                source.get(k) != row[k] for k in row):
            raise ValueError("selection proof selected row does not bind universe")
    return rows


def _nearest_index(value: Fraction) -> int:
    scaled = value * 2; floor = scaled.numerator // scaled.denominator
    return floor if scaled - floor <= Fraction(1, 2) else floor + 1


def sample_plan(proof: Mapping[str, object], contract: Mapping[str, object]):
    validate_score_contract(contract)
    offsets = [_fraction(value) for value in contract["sample_offsets_seconds"]]
    maximum = _fraction(contract["acquisition"]["maximum_nominal_to_grid_error_seconds"])
    plan = []
    for row, center in selected_centers(proof):
        samples = []; used = set()
        for offset in offsets:
            nominal = center + offset; index = _nearest_index(nominal)
            grid = Fraction(index, 2)
            if (index < 0 or index in used or abs(grid - nominal) > maximum
                    or (offset < 0) != (grid < center)):
                raise ValueError("proof-selected sample mapping is invalid")
            used.add(index); samples.append(index)
        plan.append((row, samples))
    return plan


def build_score_artifact(*, contract: Mapping[str, object],
        selection_proof: Mapping[str, object], selection_proof_sha256: str,
        source_sha256_before: str, source_sha256_after: str, frame_count: int,
        selected_frames: Mapping[int, bytes]):
    validate_score_contract(contract)
    if (selection_proof_sha256 != PROOF_SHA256
            or source_sha256_before != SOURCE_SHA256
            or source_sha256_after != SOURCE_SHA256
            or type(frame_count) is not int or frame_count <= 0):
        raise ValueError("label-free score lineage is invalid")
    scores = []
    for row, indices in sample_plan(selection_proof, contract):
        if any(index >= frame_count or index not in selected_frames for index in indices):
            raise ValueError("decoded source is missing a proof-selected sample")
        score = evaluation_metrics([selected_frames[index] for index in indices])["score"]
        if not isinstance(score, float) or not math.isfinite(score):
            raise ValueError("structural score is not finite")
        scores.append({"selection_rank": row["selection_rank"],
                       "event_id": row["event_id"], "signal_id": row["signal_id"],
                       "score": score})
    return {"schema_version": SCHEMA,
            "inputs": {"score_contract_sha256": CONTRACT_SHA256,
                       "selection_proof_sha256": selection_proof_sha256},
            "scores": scores, "privacy": PRIVACY, "authority": AUTHORITY}


def validate_score_artifact(document: Mapping[str, object], **inputs) -> None:
    if document != build_score_artifact(**inputs):
        raise ValueError("label-free score artifact must exactly derive from inputs")
