#!/usr/bin/env python3
"""Atomically assess whether one exact chapter map may enter foreshadow planning."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.chapter_map_foreshadow_eligibility import assess_chapter_map_foreshadow_eligibility  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter_map_json", type=Path)
    parser.add_argument("segment_timeline_json", type=Path)
    parser.add_argument("map_config_json", type=Path)
    parser.add_argument("qualification_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    inputs = [args.chapter_map_json, args.segment_timeline_json,
              args.map_config_json, args.qualification_json, args.policy_json]
    if not all(path.is_file() for path in inputs):
        parser.error("eligibility input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in inputs]
    values = [json.loads(value) for value in raw]
    hashes = [hashlib.sha256(value).hexdigest() for value in raw]
    document = assess_chapter_map_foreshadow_eligibility(
        *values, chapter_map_sha256=hashes[0],
        segment_timeline_sha256=hashes[1], map_config_sha256=hashes[2],
        qualification_sha256=hashes[3], policy_sha256=hashes[4],
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
    print(json.dumps({"eligible": document["eligible"],
                      "reasons": document["reasons"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
