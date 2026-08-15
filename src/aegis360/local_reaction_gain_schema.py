"""Closed grammar for one local-VLM pairwise reaction-view decision."""

from __future__ import annotations


def local_reaction_gain_json_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"decision": {"type": "string", "enum": ["promote", "abstain"]}},
        "required": ["decision"],
        "additionalProperties": False,
    }
