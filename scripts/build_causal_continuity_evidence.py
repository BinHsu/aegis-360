#!/usr/bin/env python3
"""Bind complete closed narrative-continuity observations to reviewed segments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.causal_continuity_evidence import build_causal_continuity_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_json", type=Path)
    parser.add_argument("timeline_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--packet", action="append", type=Path, default=[])
    args = parser.parse_args()
    paths = [args.config_json, args.timeline_json, args.grid_json, *args.packet]
    if not all(path.is_file() for path in paths):
        parser.error("required continuity input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    packet_raw = raw[3:]
    artifact = build_causal_continuity_evidence(
        json.loads(raw[0]), json.loads(raw[1]),
        [json.loads(value) for value in packet_raw], json.loads(raw[2]),
        config_sha256=hashlib.sha256(raw[0]).hexdigest(),
        timeline_sha256=hashlib.sha256(raw[1]).hexdigest(),
        packet_sha256s=[hashlib.sha256(value).hexdigest() for value in packet_raw],
        grid_sha256=hashlib.sha256(raw[2]).hexdigest(),
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
    print(json.dumps({"edge_count": len(artifact["edges"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
