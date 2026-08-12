"""JSON schema for geometry-owned local scene-context decisions."""

from __future__ import annotations

from typing import Mapping


FLAGS = (
    "multiple_people_visible", "face_visible", "mouth_motion_visible",
    "reciprocal_orientation", "speech_audio_present",
)


def local_context_json_schema(
    proposal: Mapping[str, object], *, audio_provided: bool,
) -> dict[str, object]:
    """Build a closed schema whose branches preserve scope/candidate coupling."""

    candidates = proposal.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("proposal candidates are missing")
    ids_by_type = {kind: [] for kind in ("person", "group", "context")}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("proposal candidate must be an object")
        identifier = candidate.get("candidate_id")
        kind = candidate.get("candidate_type")
        if not isinstance(identifier, str) or kind not in ids_by_type:
            raise ValueError("proposal candidate is invalid")
        ids_by_type[kind].append(identifier)
    branches = []
    for scope, kind in (("group", "group"), ("single", "person"), ("context", "context")):
        if ids_by_type[kind]:
            branches.append({"properties": {
                "subject_scope": {"const": scope},
                "selected_candidate_id": {"enum": ids_by_type[kind]},
            }})
    branches.append({"properties": {
        "subject_scope": {"const": "uncertain"},
        "selected_candidate_id": {"type": "null"},
    }})
    flag_properties = {
        key: {"enum": ["present", "absent", "unknown"]} for key in FLAGS
    }
    if not audio_provided:
        flag_properties["speech_audio_present"] = {"const": "unknown"}
    return {
        "type": "object", "additionalProperties": False,
        "required": [
            "context_class", "subject_scope", "selected_candidate_id",
            "evidence_flags",
        ],
        "properties": {
            "context_class": {"enum": [
                "conversation", "direct_address", "coordinated_activity",
                "ambient_people", "uncertain",
            ]},
            "subject_scope": {"enum": ["group", "single", "context", "uncertain"]},
            "selected_candidate_id": {
                "enum": sorted(sum(ids_by_type.values(), [])) + [None],
            },
            "evidence_flags": {
                "type": "object", "additionalProperties": False,
                "required": list(FLAGS), "properties": flag_properties,
            },
        },
        # The scope constants are mutually exclusive, so anyOf is equivalent to
        # oneOf while remaining supported by llguidance 1.7.6.
        "anyOf": branches,
    }
