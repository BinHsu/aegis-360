"""Closed, path-free context evidence for human or local-VLM event review."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Mapping


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
CONTEXT_CLASSES = {
    "conversation", "direct_address", "coordinated_activity",
    "ambient_people", "uncertain",
}
SUBJECT_SCOPES = {"group", "single", "context", "uncertain"}
CANDIDATE_TYPES = {"person", "group", "context"}
EVIDENCE_FLAGS = {
    "multiple_people_visible", "face_visible", "mouth_motion_visible",
    "reciprocal_orientation", "speech_audio_present",
}
FLAG_VALUES = {"present", "absent", "unknown"}
NONIDENTITY_LIMITATION = (
    "context classification does not establish identity or active speaker"
)


@dataclass(frozen=True)
class SceneContextCandidate:
    candidate_id: str
    candidate_type: str
    member_candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class SceneContextDecision:
    context_class: str
    subject_scope: str
    selected_candidate_id: str | None
    candidates: tuple[SceneContextCandidate, ...]
    evidence_flags: Mapping[str, str]


def _safe_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a privacy-safe identifier")
    return value


def validate_scene_context(document: str | bytes | Mapping[str, object]) -> SceneContextDecision:
    """Validate schema v1 and return only bounded editorial context evidence."""

    root = json.loads(document) if isinstance(document, (str, bytes)) else document
    if not isinstance(root, Mapping):
        raise ValueError("scene context must be an object")
    required = {
        "schema_version", "window", "candidates", "provenance", "decision",
        "privacy", "limitations",
    }
    if set(root) != required:
        raise ValueError("scene context fields must match the closed schema")
    if root["schema_version"] != "aegis360.scene-context.v2":
        raise ValueError("unsupported scene context schema")

    window = root["window"]
    if not isinstance(window, Mapping) or set(window) != {
        "source_id", "window_id", "start_seconds", "duration_seconds",
    }:
        raise ValueError("window fields must match the closed schema")
    _safe_id(window["source_id"], "source_id")
    _safe_id(window["window_id"], "window_id")
    for key in ("start_seconds", "duration_seconds"):
        value = window[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be finite")
    if window["start_seconds"] < 0 or window["duration_seconds"] <= 0:
        raise ValueError("scene window timing is invalid")
    candidate_values = root["candidates"]
    if not isinstance(candidate_values, list) or not candidate_values:
        raise ValueError("candidates must be a nonempty array")
    candidates = []
    for index, value in enumerate(candidate_values):
        if not isinstance(value, Mapping) or set(value) != {
            "candidate_id", "candidate_type", "member_candidate_ids",
        }:
            raise ValueError("candidate fields must match the closed schema")
        candidate_id = _safe_id(value["candidate_id"], f"candidates[{index}].candidate_id")
        candidate_type = value["candidate_type"]
        if candidate_type not in CANDIDATE_TYPES:
            raise ValueError("candidate type is unsupported")
        members_value = value["member_candidate_ids"]
        if not isinstance(members_value, list):
            raise ValueError("member_candidate_ids must be an array")
        members = tuple(_safe_id(item, "member_candidate_id") for item in members_value)
        if len(members) != len(set(members)):
            raise ValueError("group member IDs must be unique")
        if (candidate_type == "group" and len(members) < 2) or (
            candidate_type != "group" and members
        ):
            raise ValueError("candidate members conflict with candidate type")
        candidates.append(SceneContextCandidate(candidate_id, candidate_type, members))
    candidate_ids = {candidate.candidate_id for candidate in candidates}
    if len(candidate_ids) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    person_ids = {
        candidate.candidate_id for candidate in candidates
        if candidate.candidate_type == "person"
    }
    for candidate in candidates:
        if candidate.candidate_type == "group" and not set(candidate.member_candidate_ids).issubset(person_ids):
            raise ValueError("group members must reference declared person proposals")

    provenance = root["provenance"]
    if not isinstance(provenance, Mapping) or set(provenance) != {
        "reviewer_kind", "adapter_id", "model_id", "model_sha256",
    }:
        raise ValueError("provenance fields must match the closed schema")
    if provenance["reviewer_kind"] not in {"human", "local_vlm"}:
        raise ValueError("reviewer_kind must be human or local_vlm")
    _safe_id(provenance["adapter_id"], "adapter_id")
    if provenance["reviewer_kind"] == "local_vlm":
        _safe_id(provenance["model_id"], "model_id")
        checksum = provenance["model_sha256"]
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("local_vlm requires a lowercase SHA-256")
    elif provenance["model_id"] is not None or provenance["model_sha256"] is not None:
        raise ValueError("human context must not claim model provenance")

    decision = root["decision"]
    if not isinstance(decision, Mapping) or set(decision) != {
        "context_class", "subject_scope", "selected_candidate_id", "evidence_flags",
    }:
        raise ValueError("decision fields must match the closed schema")
    context_class = decision["context_class"]
    subject_scope = decision["subject_scope"]
    if context_class not in CONTEXT_CLASSES or subject_scope not in SUBJECT_SCOPES:
        raise ValueError("context class or subject scope is unsupported")
    selected_value = decision["selected_candidate_id"]
    selected = None if selected_value is None else _safe_id(selected_value, "selected_candidate_id")
    expected_type = {"group": "group", "single": "person", "context": "context"}.get(subject_scope)
    if subject_scope == "uncertain":
        if selected is not None:
            raise ValueError("uncertain scope cannot select a candidate")
    elif selected not in candidate_by_id or candidate_by_id[selected].candidate_type != expected_type:
        raise ValueError("selected candidate type conflicts with subject scope")

    flags = decision["evidence_flags"]
    if not isinstance(flags, Mapping) or set(flags) != EVIDENCE_FLAGS:
        raise ValueError("evidence flags must match the closed schema")
    if any(value not in FLAG_VALUES for value in flags.values()):
        raise ValueError("evidence flags must be present, absent, or unknown")

    privacy = root["privacy"]
    if privacy != {
        "contains_source_path": False, "contains_pixels": False,
        "contains_names": False, "contains_embeddings": False,
    }:
        raise ValueError("scene context privacy declaration is invalid")
    limitations = root["limitations"]
    if not isinstance(limitations, list) or NONIDENTITY_LIMITATION not in limitations:
        raise ValueError("scene context must retain the nonidentity limitation")
    if any(not isinstance(item, str) or not item for item in limitations):
        raise ValueError("limitations must contain nonempty strings")
    return SceneContextDecision(
        context_class, subject_scope, selected, tuple(candidates), dict(flags),
    )
