"""Raw-byte coordinator for the structural blind-review replication gate."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Mapping

from aegis360.structural_blind_review import (
    SCORE_CONTRACT_SHA256, evaluate_structural_blind_reviews,
    validate_structural_blind_evaluation, validate_structural_blind_review,
)
from aegis360.structural_blind_schedule import (
    CONFIG_SHA256, PROOF_SHA256, validate_exact_schedule,
    validate_schedule_config,
)


SCORE_SCHEMA = "aegis360.structural-chapter-label-free-scores.v1"
ATTESTATION_SCHEMA = "aegis360.structural-blind-reviewer-separation-attestation.v1"
COORDINATOR_SCHEMA = "aegis360.structural-blind-evaluation-coordinator.v1"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_constant(_: str) -> None:
    raise ValueError("JSON contains a non-finite number")


def _closed_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contains a duplicate key")
        result[key] = value
    return result


def _read_json(path: Path) -> tuple[bytes, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_closed_object,
                           parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("input could not be read as strict JSON") from error
    return raw, value


def _read_salt(path: Path) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as error:
        raise ValueError("presentation salt could not be read") from error
    if (len(raw) != 65 or raw[-1:] != b"\n" or mode & 0o077
            or any(byte not in b"0123456789abcdef" for byte in raw[:-1])):
        raise ValueError("presentation salt must be one owner-only lowercase 64-hex line")
    return raw, raw[:-1].decode("ascii")


def _validate_score_artifact(document: object) -> list[Mapping[str, object]]:
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "inputs", "scores", "privacy", "authority"}
            or document.get("schema_version") != SCORE_SCHEMA
            or document.get("inputs") != {
                "score_contract_sha256": SCORE_CONTRACT_SHA256,
                "selection_proof_sha256": PROOF_SHA256,
            }
            or document.get("privacy") != {"contains_semantic_label": False,
                                             "contains_expected_class": False,
                                             "contains_source_path": False}
            or document.get("authority") != {"structural_score": True,
                                               "semantic_boundary": False,
                                               "camera": False, "render": False}
            or not isinstance(document.get("scores"), list)):
        raise ValueError("structural score artifact is not closed or label-free")
    return document["scores"]


def _validate_attestation(document: object, slots: list[str]) -> None:
    expected = {
        "schema_version": ATTESTATION_SCHEMA,
        "reviewer_slot_ids": slots,
        "distinct_principals": True,
        "privacy": {"contains_principal_identity": False},
        "authority": {"reviewer_separation": True, "semantic_boundary": False,
                      "camera": False, "render": False},
    }
    if document != expected:
        raise ValueError("reviewer separation attestation is invalid")


def coordinate_structural_blind_evaluation(
    *, config_path: Path, proof_path: Path, private_schedule_path: Path,
    public_index_path: Path, bundle_directory: Path, salt_path: Path,
    review_a_path: Path, review_b_path: Path, score_path: Path,
    attestation_path: Path,
) -> dict[str, object]:
    config_raw, config = _read_json(config_path)
    proof_raw, proof = _read_json(proof_path)
    private_raw, private = _read_json(private_schedule_path)
    public_raw, public = _read_json(public_index_path)
    review_a_raw, review_a = _read_json(review_a_path)
    review_b_raw, review_b = _read_json(review_b_path)
    score_raw, score_document = _read_json(score_path)
    attestation_raw, attestation = _read_json(attestation_path)
    _, salt_hex = _read_salt(salt_path)
    if _digest(config_raw) != CONFIG_SHA256 or _digest(proof_raw) != PROOF_SHA256:
        raise ValueError("frozen config or selection proof checksum mismatch")
    if not all(isinstance(value, Mapping) for value in
               (config, proof, private, public, review_a, review_b, attestation)):
        raise ValueError("coordinator input has an invalid top-level type")
    validate_schedule_config(config)
    schedule_inputs = dict(selection_proof=proof, selection_proof_sha256=PROOF_SHA256,
                           config=config, config_sha256=CONFIG_SHA256,
                           presentation_salt_hex=salt_hex)
    validate_exact_schedule(private, public, **schedule_inputs)
    from aegis360.structural_blind_renderer import validate_canonical_bundle_tree
    try:
        bundled_public_raw = (bundle_directory / "public-reviewer-index.json").read_bytes()
    except OSError as error:
        raise ValueError("review bundle public index could not be read") from error
    if bundled_public_raw != public_raw:
        raise ValueError("review bundle public index differs from frozen public index")
    validate_canonical_bundle_tree(bundle_directory, public, _digest_bundle_tree(
        bundle_directory, public))
    public_ids = [packet["packet_id"] for packet in public["packets"]]
    by_packet = {entry["packet_id"]: entry for entry in private["entries"]}
    mapping = [{key: by_packet[packet][key] for key in
                ("packet_id", "selection_rank", "event_id", "signal_id")}
               for packet in public_ids]
    scores = _validate_score_artifact(score_document)
    bundle_tree_sha = _digest_bundle_tree(bundle_directory, public)
    lineage = dict(public_packet_ids=public_ids,
                   public_index_sha256=_digest(public_raw),
                   bundle_tree_sha256=bundle_tree_sha,
                   schedule_config_sha256=CONFIG_SHA256)
    validate_structural_blind_review(review_a, **lineage)
    validate_structural_blind_review(review_b, **lineage)
    slots = [review_a["reviewer_slot_id"], review_b["reviewer_slot_id"]]
    if slots[0] == slots[1]:
        raise ValueError("blind reviews require distinct reviewer slots")
    _validate_attestation(attestation, slots)
    evaluation_inputs = dict(**lineage, private_mapping=mapping,
        private_mapping_sha256=_digest(private_raw), structural_scores=scores,
        structural_scores_sha256=_digest(score_raw),
        selection_proof_sha256=PROOF_SHA256,
        score_contract_sha256=SCORE_CONTRACT_SHA256,
        review_a=review_a, review_a_sha256=_digest(review_a_raw),
        review_b=review_b, review_b_sha256=_digest(review_b_raw))
    evaluation = evaluate_structural_blind_reviews(**evaluation_inputs)
    validate_structural_blind_evaluation(evaluation, **evaluation_inputs)
    return {"schema_version": COORDINATOR_SCHEMA,
            "inputs": {"attestation_sha256": _digest(attestation_raw)},
            "evaluation": evaluation,
            "authority": {"evaluation_packaging": True,
                          "semantic_boundary": False, "camera": False, "render": False}}


def _digest_bundle_tree(bundle_directory: Path, public: Mapping[str, object]) -> str:
    from aegis360.structural_blind_renderer import canonical_bundle_tree_sha256
    return canonical_bundle_tree_sha256(bundle_directory, public)


def write_json_no_overwrite(output: Path, document: Mapping[str, object]) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite output")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    except FileExistsError as error:
        raise ValueError("refusing to overwrite output") from error
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
