#!/usr/bin/env python3
"""Build one atomic typed story-segment timeline."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.typed_story_segment_timeline import build_typed_story_segment_timeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("boundaries_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.grid_json.is_file() or not args.boundaries_json.is_file():
        parser.error("required input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    grid_raw = args.grid_json.read_bytes()
    boundaries_raw = args.boundaries_json.read_bytes()
    document = build_typed_story_segment_timeline(
        json.loads(grid_raw), json.loads(boundaries_raw),
        grid_sha256=hashlib.sha256(grid_raw).hexdigest(),
        boundaries_sha256=hashlib.sha256(boundaries_raw).hexdigest())
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
