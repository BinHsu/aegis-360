#!/usr/bin/env python3
"""Bind one closed adapter result to an exact event-review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.event_semantics import build_event_semantics  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_json", type=Path)
    parser.add_argument("packet_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.config_json.is_file() or not args.packet_json.is_file():
        parser.error("config or packet is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    config_bytes = args.config_json.read_bytes()
    packet_bytes = args.packet_json.read_bytes()
    artifact = build_event_semantics(
        json.loads(config_bytes), json.loads(packet_bytes),
        config_sha256=hashlib.sha256(config_bytes).hexdigest(),
        packet_sha256=hashlib.sha256(packet_bytes).hexdigest(),
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
