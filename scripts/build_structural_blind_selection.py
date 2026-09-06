#!/usr/bin/env python3
"""Build the exact structural blind-replication selection proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.structural_blind_selection import (  # noqa: E402
    CONFIG_SHA256, build_selection_proof, validate_selection_config,
    validate_selection_proof,
)


def _read(path: Path):
    data = path.read_bytes()
    return data, json.loads(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("context_grid", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("packets", type=Path, nargs="+")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite output")
    try:
        config_bytes, config = _read(args.config)
        timeline_bytes, timeline = _read(args.timeline)
        grid_bytes, grid = _read(args.context_grid)
        if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
            raise ValueError("config checksum does not match frozen policy")
        validate_selection_config(config)
        if hashlib.sha256(timeline_bytes).hexdigest() != config["timeline"]["sha256"]:
            raise ValueError("timeline checksum does not match frozen policy")
        if hashlib.sha256(grid_bytes).hexdigest() != config["proof_packet_contract"]["context_view_grid_sha256"]:
            raise ValueError("context grid checksum does not match frozen policy")
        packet_data = [_read(path) for path in args.packets]
        packets = [item[1] for item in packet_data]
        packet_hashes = [hashlib.sha256(item[0]).hexdigest() for item in packet_data]
        inputs = dict(config=config, config_sha256=CONFIG_SHA256,
                      timeline=timeline, timeline_sha256=config["timeline"]["sha256"],
                      grid=grid, grid_sha256=config["proof_packet_contract"]["context_view_grid_sha256"],
                      packets=packets, packet_sha256s=packet_hashes)
        artifact = build_selection_proof(**inputs)
        validate_selection_proof(artifact, **inputs)
        payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent,
             prefix=f".{args.output.name}.", suffix=".tmp", delete=False) as stage:
            stage.write(payload); stage_name = stage.name
        try:
            os.link(stage_name, args.output)
        finally:
            Path(stage_name).unlink(missing_ok=True)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) else "input or output could not be read"
        parser.error(message)
    print(json.dumps({"selected_count": len(artifact["selected"]),
                      "universe_count": len(artifact["universe"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
