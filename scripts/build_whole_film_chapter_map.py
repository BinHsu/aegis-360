#!/usr/bin/env python3
"""Build one atomic, candidate-free whole-film chapter map."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.whole_film_chapter_map import build_whole_film_chapter_map  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segment_timeline_json", type=Path)
    parser.add_argument("config_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.segment_timeline_json.is_file() or not args.config_json.is_file():
        parser.error("segment timeline or chapter-map config is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    timeline_raw = args.segment_timeline_json.read_bytes()
    config_raw = args.config_json.read_bytes()
    document = build_whole_film_chapter_map(
        json.loads(timeline_raw), json.loads(config_raw),
        segment_timeline_sha256=hashlib.sha256(timeline_raw).hexdigest(),
        config_sha256=hashlib.sha256(config_raw).hexdigest(),
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
    print(json.dumps({"boundary_count": len(document["boundary_accounting"]),
                      "chapter_count": len(document["chapters"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
