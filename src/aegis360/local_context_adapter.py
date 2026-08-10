"""Adapt one closed local-model decision to scene-context v2."""

from __future__ import annotations

import re
from typing import Mapping

from .scene_context import EVIDENCE_FLAGS, NONIDENTITY_LIMITATION, validate_scene_context


SHA256 = re.compile(r"^[0-9a-f]{64}$")
DECISION_FIELDS = {
    "context_class", "subject_scope", "selected_candidate_id", "evidence_flags",
}


def build_local_context_document(
    proposal: Mapping[str, object],
    model_decision: Mapping[str, object],
    *,
    adapter_id: str,
    model_id: str,
    model_sha256: str,
) -> dict[str, object]:
    """Bind closed model output to geometry-owned proposals and validate it."""

    if proposal.get("schema_version") != "aegis360.window-group-proposal.v1":
        raise ValueError("unsupported proposal schema")
    if set(model_decision) != DECISION_FIELDS:
        raise ValueError("model decision fields must match the closed schema")
    flags = model_decision.get("evidence_flags")
    if not isinstance(flags, Mapping) or set(flags) != EVIDENCE_FLAGS:
        raise ValueError("model evidence flags must match the closed schema")
    if not isinstance(model_sha256, str) or not SHA256.fullmatch(model_sha256):
        raise ValueError("model SHA-256 must be lowercase hexadecimal")
    window = proposal.get("window")
    candidates = proposal.get("candidates")
    if not isinstance(window, Mapping) or not isinstance(candidates, list):
        raise ValueError("proposal is incomplete")
    document = {
        "schema_version": "aegis360.scene-context.v2",
        "window": {
            key: window[key] for key in (
                "source_id", "window_id", "start_seconds", "duration_seconds",
            )
        },
        "candidates": candidates,
        "provenance": {
            "reviewer_kind": "local_vlm", "adapter_id": adapter_id,
            "model_id": model_id, "model_sha256": model_sha256,
        },
        "decision": dict(model_decision),
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_embeddings": False,
        },
        "limitations": [NONIDENTITY_LIMITATION],
    }
    validate_scene_context(document)
    return document
