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
EVIDENCE_FLAGS = {
    "multiple_people_visible", "face_visible", "mouth_motion_visible",
    "reciprocal_orientation", "speech_audio_present",
}
FLAG_VALUES = {"present", "absent", "unknown"}
NONIDENTITY_LIMITATION = (
    "context classification does not establish identity or active speaker"
)


@dataclass(frozen=True)
class SceneContextDecision:
    context_class: str
    subject_scope: str
    selected_candidate_ids: tuple[str, ...]
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
    required = {"schema_version", "window", "provenance", "decision", "privacy", "limitations"}
    if set(root) != required:
        raise ValueError("scene context fields must match the closed schema")
    if root["schema_version"] != "aegis360.scene-context.v1":
        raise ValueError("unsupported scene context schema")

    window = root["window"]
    if not isinstance(window, Mapping) or set(window) != {
        "source_id", "window_id", "start_seconds", "duration_seconds", "candidate_ids",
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
    candidate_ids = window["candidate_ids"]
    if not isinstance(candidate_ids, list) or not candidate_ids:
        raise ValueError("candidate_ids must be a nonempty array")
    candidates = tuple(_safe_id(value, "candidate_id") for value in candidate_ids)
    if len(candidates) != len(set(candidates)):
        raise ValueError("candidate_ids must be unique")

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
        "context_class", "subject_scope", "selected_candidate_ids", "evidence_flags",
    }:
        raise ValueError("decision fields must match the closed schema")
    context_class = decision["context_class"]
    subject_scope = decision["subject_scope"]
    if context_class not in CONTEXT_CLASSES or subject_scope not in SUBJECT_SCOPES:
        raise ValueError("context class or subject scope is unsupported")
    selected_value = decision["selected_candidate_ids"]
    if not isinstance(selected_value, list):
        raise ValueError("selected_candidate_ids must be an array")
    selected = tuple(_safe_id(value, "selected_candidate_id") for value in selected_value)
    if len(selected) != len(set(selected)) or not set(selected).issubset(candidates):
        raise ValueError("selected candidates must be unique declared candidates")
    required_count = 2 if subject_scope == "group" else 1 if subject_scope == "single" else 0
    if (subject_scope == "group" and len(selected) < required_count) or (
        subject_scope != "group" and len(selected) != required_count
    ):
        raise ValueError("selected candidate count conflicts with subject scope")

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
    return SceneContextDecision(context_class, subject_scope, selected, dict(flags))
