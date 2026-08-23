#!/usr/bin/env python3
"""Build one atomic candidate-view packet scoped inside a story segment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.story_segment_review_packet import build_story_segment_review_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segment_timeline_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("segment_id")
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.segment_timeline_json.is_file() or not args.grid_json.is_file():
        parser.error("segment timeline or grid is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    timeline_raw = args.segment_timeline_json.read_bytes()
    grid_raw = args.grid_json.read_bytes()
    document = build_story_segment_review_packet(
        json.loads(timeline_raw), json.loads(grid_raw), segment_id=args.segment_id,
        segment_timeline_sha256=hashlib.sha256(timeline_raw).hexdigest(),
        grid_sha256=hashlib.sha256(grid_raw).hexdigest(),
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
    print(json.dumps({"sample_count": len(document["samples"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
