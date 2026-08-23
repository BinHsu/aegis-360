#!/usr/bin/env python3
"""Build atomic candidate-free planner constraints from ordered story evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.story_planner_constraints import build_story_planner_constraints  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--semantic", type=Path, action="append", required=True)
    parser.add_argument("--packet", type=Path, action="append", required=True)
    args = parser.parse_args()
    inputs = [args.policy_json, *args.semantic, *args.packet]
    if not all(path.is_file() for path in inputs) or len(args.semantic) != len(args.packet):
        parser.error("policy or paired story evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    policy_raw = args.policy_json.read_bytes()
    semantic_raw = [path.read_bytes() for path in args.semantic]
    packet_raw = [path.read_bytes() for path in args.packet]
    document = build_story_planner_constraints(
        [json.loads(value) for value in semantic_raw],
        [json.loads(value) for value in packet_raw], json.loads(policy_raw),
        semantics_sha256s=[hashlib.sha256(value).hexdigest() for value in semantic_raw],
        packet_sha256s=[hashlib.sha256(value).hexdigest() for value in packet_raw],
        policy_sha256=hashlib.sha256(policy_raw).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=args.output_json.parent, delete=False) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"constraint_count": len(document["constraints"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
