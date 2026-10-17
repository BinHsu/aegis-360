"""Pure-JSON upstream rebuild preflight for a supplied Stage A v2 timeline.

This proves only derivation from caller-supplied cheap-signal JSON bytes. It
does not authenticate source media, cheap-signal extraction, or model output.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from .multi_signal_timeline import build_multi_signal_timeline


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SCENE_CONTEXT_SECONDS = 2.0


def _parse(raw: bytes, name: str) -> Mapping[str, object]:
    if not isinstance(raw, bytes):
        raise ValueError(f"{name} must be exact JSON bytes")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"{name} has duplicate JSON keys")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"{name} contains nonfinite {value}")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=nonfinite)
        # Python's JSON decoder also accepts overflowing numeric literals.
        json.dumps(result, allow_nan=False)
    except (UnicodeError, json.JSONDecodeError, OverflowError, TypeError) as error:
        raise ValueError(f"{name} is invalid JSON") from error
    if not isinstance(result, dict):
        raise ValueError(f"{name} must be a JSON object")
    return result


def _canonical(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=True,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_stage_a_timeline_upstream(*, grid_bytes: bytes,
        scene_candidates_bytes: bytes, timeline_bytes: bytes,
        timeline_sha256: str,
        reaction_timeline_bytes: bytes | None = None) -> None:
    """Reject a v2 timeline unless the frozen builder exactly reproduces it.

    The expected timeline SHA comes from a separate frozen declaration (for
    example the Stage A lineage manifest), never from the timeline itself.
    """
    if not isinstance(timeline_sha256, str) or _SHA.fullmatch(timeline_sha256) is None:
        raise ValueError("declared Stage A timeline SHA-256 is invalid")
    grid = _parse(grid_bytes, "context grid")
    scenes = _parse(scene_candidates_bytes, "scene candidates")
    timeline = _parse(timeline_bytes, "v2 timeline")
    reaction = None if reaction_timeline_bytes is None else _parse(
        reaction_timeline_bytes, "reaction timeline")
    grid_sha = hashlib.sha256(grid_bytes).hexdigest()
    scene_sha = hashlib.sha256(scene_candidates_bytes).hexdigest()
    reaction_sha = (None if reaction_timeline_bytes is None else
                    hashlib.sha256(reaction_timeline_bytes).hexdigest())
    if hashlib.sha256(timeline_bytes).hexdigest() != timeline_sha256:
        raise ValueError("v2 timeline raw-byte SHA-256 differs from declaration")
    if (timeline.get("inputs") != {
            "context_view_grid_sha256": grid_sha,
            "scene_change_candidates_sha256": scene_sha,
            "reaction_timeline_sha256": reaction_sha}):
        raise ValueError("v2 timeline upstream raw-byte SHA-256 differs")
    try:
        rebuilt = build_multi_signal_timeline(
            grid, scenes, grid_sha256=grid_sha,
            scene_candidates_sha256=scene_sha,
            reaction_timeline=reaction, reaction_timeline_sha256=reaction_sha,
            scene_context_seconds=_SCENE_CONTEXT_SECONDS)
        if _canonical(timeline) != _canonical(rebuilt):
            raise ValueError("v2 timeline does not exactly rebuild from upstream")
    except (KeyError, TypeError, IndexError, OverflowError) as error:
        raise ValueError("v2 timeline upstream evidence is invalid") from error
