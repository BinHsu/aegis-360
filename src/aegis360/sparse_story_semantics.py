"""Closed sparse-story observations, binding, and operational failures."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping


RAW_SCHEMA = "aegis360.sparse-story-raw-observation.v1"
EVIDENCE_SCHEMA = "aegis360.sparse-story-semantic-evidence.v1"
FAILURE_SCHEMA = "aegis360.sparse-story-operational-failure.v1"
SHA = re.compile(r"^[0-9a-f]{64}$")
PACKET = re.compile(r"^packet-[0-9a-f]{20}$")
FIELDS = ("status", "early_state_coherence", "late_state_coherence",
          "activity_relation", "setting_relation",
          "anonymous_participant_configuration", "transition_support",
          "viewpoint_change", "foreground_rearrangement",
          "exposure_or_palette_change", "capture_or_projection_artifact")
VALUES = {
    "status": {"observed", "abstain"},
    "early_state_coherence": {"observed", "not_observed", "unclear"},
    "late_state_coherence": {"observed", "not_observed", "unclear"},
    "activity_relation": {"same", "changed", "unclear"},
    "setting_relation": {"same", "changed", "unclear"},
    "anonymous_participant_configuration": {"same", "changed", "unclear"},
    "transition_support": {"supports", "contradicts", "insufficient"},
    "viewpoint_change": {"present", "absent", "unclear"},
    "foreground_rearrangement": {"present", "absent", "unclear"},
    "exposure_or_palette_change": {"present", "absent", "unclear"},
    "capture_or_projection_artifact": {"present", "absent", "unclear"},
}
FAILURE_REASONS = {"missing_anchor", "invocation_failure", "malformed_json",
                   "forbidden_field", "schema_violation"}
ABSTENTION = {field: ("abstain" if field == "status" else
                      "insufficient" if field == "transition_support" else "unclear")
              for field in FIELDS}
PRIVACY = {"contains_source_path": False, "contains_source_time": False,
           "contains_source_id": False, "contains_source_position": False,
           "contains_signal": False, "contains_expected_class": False,
           "contains_event_id": False, "contains_identity": False,
           "contains_confidence": False, "contains_geometry": False,
           "contains_candidate_views": False, "contains_chapter_label": False,
           "contains_narrative_function": False,
           "contains_edit_command": False, "contains_edit_request": False,
           "contains_raw_output": False,
           "contains_stderr": False, "contains_free_text": False}
AUTHORITY = {"semantic_observation": True, "exact_boundary": False,
             "chapter_map": False, "camera": False, "reorder": False,
             "render": False}


def _hashes(**values):
    if any(not isinstance(value, str) or SHA.fullmatch(value) is None
           for value in values.values()):
        raise ValueError("sparse-story input checksum is invalid")


def validate_raw_observation(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping) or set(document) != set(FIELDS):
        raise ValueError("sparse-story raw observation schema is invalid")
    if any(not isinstance(document[field], str)
           or document[field] not in VALUES[field] for field in FIELDS):
        raise ValueError("sparse-story raw observation value is invalid")
    if document["status"] == "abstain" and dict(document) != ABSTENTION:
        raise ValueError("sparse-story abstention must be canonical")


def derive_event_class(raw: Mapping[str, object]) -> str:
    validate_raw_observation(raw)
    if raw["status"] != "observed":
        return "abstain"
    if raw["capture_or_projection_artifact"] == "present":
        return "capture_artifact"
    coherent = (raw["early_state_coherence"] == "observed"
                and raw["late_state_coherence"] == "observed")
    nuisances_absent = all(raw[field] == "absent" for field in
        ("viewpoint_change", "foreground_rearrangement",
         "exposure_or_palette_change", "capture_or_projection_artifact"))
    if (coherent and (raw["activity_relation"] == "changed"
                      or raw["setting_relation"] == "changed")
            and raw["transition_support"] == "supports" and nuisances_absent):
        return "story_change"
    participant_ok = (raw["anonymous_participant_configuration"] == "same"
        or (raw["anonymous_participant_configuration"] == "changed"
            and (raw["viewpoint_change"] == "present"
                 or raw["foreground_rearrangement"] == "present")))
    if (coherent and raw["activity_relation"] == "same"
            and raw["setting_relation"] == "same"
            and raw["capture_or_projection_artifact"] == "absent"
            and raw["exposure_or_palette_change"] == "absent" and participant_ok):
        return "no_semantic_change"
    return "abstain"


def _decode_raw(raw_output: bytes) -> object:
    if not isinstance(raw_output, bytes):
        raise ValueError("raw adapter output must be exact bytes")
    def reject(_): raise ValueError("raw adapter output contains non-finite JSON")
    def closed(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("raw adapter output contains duplicate key")
            result[key] = value
        return result
    try:
        return json.loads(raw_output.decode("utf-8"), parse_constant=reject,
                          object_pairs_hook=closed)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("raw adapter output is malformed JSON") from error
def _strict_raw(raw_output: bytes) -> Mapping[str, object]:
    parsed = _decode_raw(raw_output)
    if not isinstance(parsed, Mapping):
        raise ValueError("raw adapter output top level must be an object")
    validate_raw_observation(parsed)
    return parsed


def bind_observation(*, packet_id: str, private_packet_sha256: str,
        adapter_projection_sha256: str, model_asset_sha256: str,
        prompt_schema_bundle_sha256: str,
        raw_output: bytes) -> dict[str, object]:
    raw_observation = _strict_raw(raw_output)
    return _bind_observation(packet_id=packet_id,
        private_packet_sha256=private_packet_sha256,
        adapter_projection_sha256=adapter_projection_sha256,
        model_asset_sha256=model_asset_sha256,
        prompt_schema_bundle_sha256=prompt_schema_bundle_sha256,
        raw_output_sha256=hashlib.sha256(raw_output).hexdigest(),
        raw_observation=raw_observation,
        operational_failure_sha256=None)


def _bind_observation(*, packet_id: str, private_packet_sha256: str,
        adapter_projection_sha256: str, model_asset_sha256: str,
        prompt_schema_bundle_sha256: str, raw_output_sha256: str,
        raw_observation: Mapping[str, object],
        operational_failure_sha256: str | None) -> dict[str, object]:
    if not isinstance(packet_id, str) or PACKET.fullmatch(packet_id) is None:
        raise ValueError("sparse-story packet ID is invalid")
    _hashes(private_packet_sha256=private_packet_sha256,
            adapter_projection_sha256=adapter_projection_sha256,
            model_asset_sha256=model_asset_sha256,
            prompt_schema_bundle_sha256=prompt_schema_bundle_sha256,
            raw_output_sha256=raw_output_sha256)
    validate_raw_observation(raw_observation)
    event_class = derive_event_class(raw_observation)
    if operational_failure_sha256 is not None and (
          SHA.fullmatch(operational_failure_sha256) is None
          or dict(raw_observation) != ABSTENTION or event_class != "abstain"):
        raise ValueError("operational failure requires canonical abstention")
    return {"schema_version": EVIDENCE_SCHEMA, "packet_id": packet_id,
        "inputs": {"private_packet_sha256": private_packet_sha256,
                   "adapter_projection_sha256": adapter_projection_sha256,
                   "model_asset_sha256": model_asset_sha256,
                   "prompt_schema_bundle_sha256": prompt_schema_bundle_sha256,
                   "raw_output_sha256": raw_output_sha256,
                   "operational_failure_sha256": operational_failure_sha256},
        "raw_observation": dict(raw_observation), "event_class": event_class,
        "privacy": dict(PRIVACY), "authority": dict(AUTHORITY)}


def validate_bound_observation(document: Mapping[str, object], **inputs) -> None:
    if document != bind_observation(**inputs):
        raise ValueError("sparse-story evidence must exactly derive from inputs")


def select_failure_reason(*, missing_anchor: bool, invocation_failed: bool,
                          raw_output: bytes) -> str | None:
    if not isinstance(raw_output, bytes):
        raise ValueError("captured stdout must be exact bytes")
    if any(type(value) is not bool for value in
           (missing_anchor, invocation_failed)):
        raise ValueError("operational state flags must be booleans")
    if missing_anchor:
        return "missing_anchor"
    if invocation_failed:
        return "invocation_failure"
    try:
        parsed_output = _decode_raw(raw_output)
    except ValueError:
        return "malformed_json"
    if isinstance(parsed_output, Mapping) and any(key not in FIELDS for key in parsed_output):
        return "forbidden_field"
    try:
        validate_raw_observation(parsed_output)  # type: ignore[arg-type]
    except ValueError:
        return "schema_violation"
    return None


def build_operational_failure(*, packet_id: str, private_packet_sha256: str,
        adapter_projection_sha256: str, model_asset_sha256: str,
        prompt_schema_bundle_sha256: str, raw_output: bytes,
        missing_anchor: bool, invocation_failed: bool) -> dict[str, object]:
    if not isinstance(packet_id, str) or PACKET.fullmatch(packet_id) is None:
        raise ValueError("sparse-story packet ID is invalid")
    _hashes(private_packet_sha256=private_packet_sha256,
            adapter_projection_sha256=adapter_projection_sha256,
            model_asset_sha256=model_asset_sha256,
            prompt_schema_bundle_sha256=prompt_schema_bundle_sha256)
    if not isinstance(raw_output, bytes):
        raise ValueError("captured stdout must be exact bytes")
    reason = select_failure_reason(missing_anchor=missing_anchor,
        invocation_failed=invocation_failed, raw_output=raw_output)
    if reason not in FAILURE_REASONS:
        raise ValueError("successful observation cannot produce a failure artifact")
    return {"schema_version": FAILURE_SCHEMA, "packet_id": packet_id,
        "inputs": {"private_packet_sha256": private_packet_sha256,
                   "adapter_projection_sha256": adapter_projection_sha256,
                   "model_asset_sha256": model_asset_sha256,
                   "prompt_schema_bundle_sha256": prompt_schema_bundle_sha256},
        "reason": reason, "raw_output_present": bool(raw_output),
        "raw_output_sha256": hashlib.sha256(raw_output).hexdigest(),
        "privacy": dict(PRIVACY),
        "authority": {"operational_failure": True, "semantic_boundary": False,
                      "camera": False, "reorder": False, "render": False}}


def validate_operational_failure(document: Mapping[str, object], **inputs) -> None:
    if document != build_operational_failure(**inputs):
        raise ValueError("operational failure must exactly derive from captured state")


def bind_failure_abstention(*, failure: Mapping[str, object], raw_output: bytes,
        missing_anchor: bool, invocation_failed: bool) -> dict[str, object]:
    validate_failure_shape(failure)
    validate_operational_failure(failure, packet_id=failure.get("packet_id"),
        private_packet_sha256=failure.get("inputs", {}).get("private_packet_sha256"),
        adapter_projection_sha256=failure.get("inputs", {}).get("adapter_projection_sha256"),
        model_asset_sha256=failure.get("inputs", {}).get("model_asset_sha256"),
        prompt_schema_bundle_sha256=failure.get("inputs", {}).get("prompt_schema_bundle_sha256"),
        raw_output=raw_output, missing_anchor=missing_anchor,
        invocation_failed=invocation_failed)
    failure_sha256 = hashlib.sha256(canonical_failure_bytes(failure)).hexdigest()
    inputs = failure["inputs"]
    return _bind_observation(packet_id=failure["packet_id"],
        private_packet_sha256=inputs["private_packet_sha256"],
        adapter_projection_sha256=inputs["adapter_projection_sha256"],
        model_asset_sha256=inputs["model_asset_sha256"],
        prompt_schema_bundle_sha256=inputs["prompt_schema_bundle_sha256"],
        raw_output_sha256=failure["raw_output_sha256"],
        raw_observation=ABSTENTION,
        operational_failure_sha256=failure_sha256)


def validate_failure_bound_observation(document: Mapping[str, object], **inputs) -> None:
    if document != bind_failure_abstention(**inputs):
        raise ValueError("failure-bound abstention must exactly derive from captured state")


def canonical_failure_bytes(failure: Mapping[str, object]) -> bytes:
    """Canonical UTF-8, ASCII-escaped, sorted compact JSON with no newline."""
    return json.dumps(failure, allow_nan=False, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def validate_failure_shape(failure: Mapping[str, object]) -> None:
    if (not isinstance(failure, Mapping)
            or set(failure) != {"schema_version", "packet_id", "inputs", "reason",
                                "raw_output_present", "raw_output_sha256",
                                "privacy", "authority"}
            or failure.get("schema_version") != FAILURE_SCHEMA
            or not isinstance(failure.get("packet_id"), str)
            or PACKET.fullmatch(failure["packet_id"]) is None
            or not isinstance(failure.get("inputs"), Mapping)
            or set(failure["inputs"]) != {"private_packet_sha256",
                "adapter_projection_sha256", "model_asset_sha256",
                "prompt_schema_bundle_sha256"}
            or any(not isinstance(value, str) or SHA.fullmatch(value) is None
                   for value in failure["inputs"].values())
            or not isinstance(failure.get("reason"), str)
            or failure["reason"] not in FAILURE_REASONS
            or type(failure.get("raw_output_present")) is not bool
            or not isinstance(failure.get("raw_output_sha256"), str)
            or SHA.fullmatch(failure["raw_output_sha256"]) is None
            or (failure.get("raw_output_present") is False
                and failure.get("raw_output_sha256")
                != hashlib.sha256(b"").hexdigest())
            or (failure.get("raw_output_present") is True
                and failure.get("raw_output_sha256")
                == hashlib.sha256(b"").hexdigest())
            or failure.get("privacy") != PRIVACY
            or failure.get("authority") != {"operational_failure": True,
                 "semantic_boundary": False, "camera": False,
                 "reorder": False, "render": False}):
        raise ValueError("operational failure shape is invalid")
