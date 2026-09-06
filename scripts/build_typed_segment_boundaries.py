#!/usr/bin/env python3
"""Build one atomic typed continuous-onset boundary artifact."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.typed_segment_boundaries import build_typed_segment_boundaries  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("onset_json", "samples_json", "grid_json", "policy_json",
                 "output_json"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--packet", type=Path, action="append", required=True)
    parser.add_argument("--evidence", type=Path, action="append", required=True)
    args = parser.parse_args()
    paths = [args.onset_json, args.samples_json, args.grid_json, args.policy_json,
             *args.packet, *args.evidence]
    if not all(path.is_file() for path in paths):
        parser.error("required input is missing")
    if len(args.packet) != len(args.evidence):
        parser.error("packet and evidence counts must match")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = {path: path.read_bytes() for path in paths}
    packets = [json.loads(raw[path]) for path in args.packet]
    evidences = [json.loads(raw[path]) for path in args.evidence]
    document = build_typed_segment_boundaries(
        json.loads(raw[args.onset_json]), json.loads(raw[args.samples_json]),
        json.loads(raw[args.grid_json]), packets, evidences,
        json.loads(raw[args.policy_json]),
        onset_sha256=hashlib.sha256(raw[args.onset_json]).hexdigest(),
        samples_sha256=hashlib.sha256(raw[args.samples_json]).hexdigest(),
        grid_sha256=hashlib.sha256(raw[args.grid_json]).hexdigest(),
        packet_sha256s=[hashlib.sha256(raw[path]).hexdigest() for path in args.packet],
        evidence_sha256s=[hashlib.sha256(raw[path]).hexdigest() for path in args.evidence],
        policy_sha256=hashlib.sha256(raw[args.policy_json]).hexdigest())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
            dir=args.output_json.parent, prefix=f".{args.output_json.name}.",
            suffix=".tmp", delete=False) as temporary:
        name = temporary.name
        temporary.write(payload)
    try:
        os.link(name, args.output_json)
    finally:
        Path(name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
