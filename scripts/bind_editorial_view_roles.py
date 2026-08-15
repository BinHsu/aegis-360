#!/usr/bin/env python3
"""Bind human editorial roles to an immutable context-view grid."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.editorial_roles import build_editorial_roles  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--primary-candidate-id", required=True)
    parser.add_argument("--reaction-candidate-id", required=True)
    parser.add_argument("--adapter-id", required=True)
    args = parser.parse_args()
    if not args.grid_json.is_file():
        parser.error("context-view grid is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    grid_bytes = args.grid_json.read_bytes()
    artifact = build_editorial_roles(
        json.loads(grid_bytes), grid_sha256=hashlib.sha256(grid_bytes).hexdigest(),
        primary_candidate_id=args.primary_candidate_id,
        reaction_candidate_id=args.reaction_candidate_id,
        adapter_id=args.adapter_id,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.output_json.parent,
        prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
    ) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
