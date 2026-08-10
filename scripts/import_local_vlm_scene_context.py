#!/usr/bin/env python3
"""Import closed local-VLM output as an atomic scene-context v2 artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.local_context_adapter import build_local_context_document  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal_json", type=Path)
    parser.add_argument("model_decision_json", type=Path)
    parser.add_argument("model_asset", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    args = parser.parse_args()
    for path in (args.proposal_json, args.model_decision_json, args.model_asset):
        if not path.is_file():
            parser.error(f"required input is missing: {path.name}")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    measured = sha256_file(args.model_asset)
    if measured != args.expected_model_sha256:
        parser.error("model asset SHA-256 mismatch")
    document = build_local_context_document(
        json.loads(args.proposal_json.read_text(encoding="utf-8")),
        json.loads(args.model_decision_json.read_text(encoding="utf-8")),
        adapter_id=args.adapter_id, model_id=args.model_id, model_sha256=measured,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
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
