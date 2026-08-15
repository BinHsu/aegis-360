#!/usr/bin/env python3
"""Build a checksummed global DP plan from utility/packet pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.global_event_planner import plan_global_events  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("utility_packet_pairs", nargs="+", type=Path)
    args = parser.parse_args()
    if len(args.utility_packet_pairs) % 2:
        parser.error("inputs must alternate utility JSON and packet JSON")
    paths = [args.policy_json, *args.utility_packet_pairs]
    if not all(path.is_file() for path in paths):
        parser.error("required planner input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    policy_bytes = args.policy_json.read_bytes()
    utility_paths = args.utility_packet_pairs[0::2]
    packet_paths = args.utility_packet_pairs[1::2]
    utility_bytes = [path.read_bytes() for path in utility_paths]
    packet_bytes = [path.read_bytes() for path in packet_paths]
    artifact = plan_global_events(
        [json.loads(value) for value in utility_bytes],
        [json.loads(value) for value in packet_bytes], json.loads(policy_bytes),
        utility_sha256s=[hashlib.sha256(value).hexdigest() for value in utility_bytes],
        packet_sha256s=[hashlib.sha256(value).hexdigest() for value in packet_bytes],
        policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
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
    print(json.dumps({"event_count": len(artifact["decisions"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
