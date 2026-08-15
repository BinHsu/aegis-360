#!/usr/bin/env python3
"""Build explainable candidate utility without selecting a camera view."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.event_utility import build_event_candidate_utility  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("semantics_json", "packet_json", "policy_json", "output_json"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = (args.semantics_json, args.packet_json, args.policy_json)
    if not all(path.is_file() for path in paths):
        parser.error("required input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    documents = [json.loads(value) for value in raw]
    artifact = build_event_candidate_utility(
        documents[0], documents[1], documents[2],
        semantics_sha256=hashlib.sha256(raw[0]).hexdigest(),
        packet_sha256=hashlib.sha256(raw[1]).hexdigest(),
        policy_sha256=hashlib.sha256(raw[2]).hexdigest(),
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
