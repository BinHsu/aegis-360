#!/usr/bin/env python3
"""Apply one closed human scene-context selection to a geometry proposal."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.scene_context import (  # noqa: E402
    EVIDENCE_FLAGS, FLAG_VALUES, NONIDENTITY_LIMITATION,
    validate_scene_context,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--context-class", required=True)
    parser.add_argument("--subject-scope", required=True)
    parser.add_argument("--selected-candidate-id")
    for name in sorted(EVIDENCE_FLAGS):
        parser.add_argument(
            "--" + name.replace("_", "-"), choices=sorted(FLAG_VALUES),
            default="unknown",
        )
    args = parser.parse_args()
    if not args.proposal_json.is_file():
        parser.error("proposal JSON is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    proposal = json.loads(args.proposal_json.read_text(encoding="utf-8"))
    if proposal.get("schema_version") != "aegis360.window-group-proposal.v1":
        parser.error("unsupported proposal schema")
    window = proposal.get("window")
    candidates = proposal.get("candidates")
    if not isinstance(window, dict) or not isinstance(candidates, list):
        parser.error("proposal is incomplete")
    document = {
        "schema_version": "aegis360.scene-context.v2",
        "window": {
            key: window[key] for key in (
                "source_id", "window_id", "start_seconds", "duration_seconds",
            )
        },
        "candidates": candidates,
        "provenance": {
            "reviewer_kind": "human", "adapter_id": args.adapter_id,
            "model_id": None, "model_sha256": None,
        },
        "decision": {
            "context_class": args.context_class,
            "subject_scope": args.subject_scope,
            "selected_candidate_id": args.selected_candidate_id,
            "evidence_flags": {
                name: getattr(args, name) for name in EVIDENCE_FLAGS
            },
        },
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_embeddings": False,
        },
        "limitations": [NONIDENTITY_LIMITATION],
    }
    decision = validate_scene_context(document)
    # Round-trip through the validated value to catch accidental schema drift.
    assert decision.selected_candidate_id == args.selected_candidate_id
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output_json.parent,
            prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(payload)
        try:
            os.link(temporary_name, args.output_json)
        except FileExistsError:
            parser.error("refusing to overwrite output")
        Path(temporary_name).unlink()
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
