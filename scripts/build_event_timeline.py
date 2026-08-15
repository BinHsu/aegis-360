#!/usr/bin/env python3
"""Build one atomic sparse event timeline from low-cost evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.event_timeline import build_event_timeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "grid_json", "roles_json", "reactions_json", "availability_json", "output_json",
    ):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = (
        args.grid_json, args.roles_json, args.reactions_json, args.availability_json,
    )
    if not all(path.is_file() for path in paths):
        parser.error("required evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    docs = [json.loads(value) for value in raw]
    artifact = build_event_timeline(
        docs[0], docs[1], docs[2], docs[3],
        grid_sha256=hashlib.sha256(raw[0]).hexdigest(),
        roles_sha256=hashlib.sha256(raw[1]).hexdigest(),
        reactions_sha256=hashlib.sha256(raw[2]).hexdigest(),
        availability_sha256=hashlib.sha256(raw[3]).hexdigest(),
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
    print(json.dumps({"event_count": len(artifact["events"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
