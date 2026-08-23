#!/usr/bin/env python3
"""Build a complete transition-utility matrix from continuity evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.continuity_transition_utility import build_continuity_transition_utility  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("evidence_json", "grid_json", "policy_json", "output_json"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = (args.evidence_json, args.grid_json, args.policy_json)
    if not all(path.is_file() for path in paths):
        parser.error("required transition-utility input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    artifact = build_continuity_transition_utility(
        *(json.loads(value) for value in raw),
        evidence_sha256=hashlib.sha256(raw[0]).hexdigest(),
        grid_sha256=hashlib.sha256(raw[1]).hexdigest(),
        policy_sha256=hashlib.sha256(raw[2]).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=args.output_json.parent, delete=False) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"edge_count": len(artifact["edge_utilities"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
