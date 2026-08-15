"""Constrained raw-output schema for a local event-semantic adapter."""


def local_event_semantics_json_schema(candidate_ids: list[str]) -> dict[str, object]:
    observation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["candidate_id", "visibility", "event_relevance", "temporal_consistency"],
        "properties": {
            "candidate_id": {"enum": candidate_ids},
            "visibility": {"enum": ["clear", "partial", "obstructed", "unknown"]},
            "event_relevance": {"enum": ["primary", "supporting", "unrelated", "unknown"]},
            "temporal_consistency": {"enum": ["stable", "changing", "unknown"]},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "event_class", "view_relationship", "candidate_observations"],
        "properties": {
            "status": {"enum": ["observed", "abstain"]},
            "event_class": {"enum": ["audience_reaction", "performance_continuation", "ambient_activity", "unknown"]},
            "view_relationship": {"enum": ["complements_current", "duplicates_current", "unrelated", "unknown"]},
            "candidate_observations": {"type": "array", "maxItems": len(candidate_ids), "items": observation},
        },
    }
