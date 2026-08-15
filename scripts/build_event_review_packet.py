#!/usr/bin/env python3
"""Build one atomic pixel-free sparse event review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.event_review_packet import build_event_review_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("event_id")
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.timeline_json.is_file() or not args.grid_json.is_file():
        parser.error("required evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    timeline_bytes = args.timeline_json.read_bytes()
    grid_bytes = args.grid_json.read_bytes()
    packet = build_event_review_packet(
        json.loads(timeline_bytes), json.loads(grid_bytes), event_id=args.event_id,
        timeline_sha256=hashlib.sha256(timeline_bytes).hexdigest(),
        grid_sha256=hashlib.sha256(grid_bytes).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(packet, allow_nan=False, indent=2, sort_keys=True) + "\n"
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
    print(json.dumps({"event_id": args.event_id, "sample_count": 5}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
