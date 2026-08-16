#!/usr/bin/env python3
"""Build one atomic Event Timeline v2 from neutral and optional role signals."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.multi_signal_timeline import build_multi_signal_timeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("scene_candidates_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--reaction-timeline", type=Path)
    parser.add_argument("--scene-context-seconds", type=float, default=2.0)
    args = parser.parse_args()
    inputs = [args.grid_json, args.scene_candidates_json]
    if args.reaction_timeline is not None:
        inputs.append(args.reaction_timeline)
    if not all(path.is_file() for path in inputs):
        parser.error("required evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in inputs]
    reaction = None if len(raw) == 2 else json.loads(raw[2])
    artifact = build_multi_signal_timeline(
        json.loads(raw[0]), json.loads(raw[1]),
        grid_sha256=hashlib.sha256(raw[0]).hexdigest(),
        scene_candidates_sha256=hashlib.sha256(raw[1]).hexdigest(),
        reaction_timeline=reaction,
        reaction_timeline_sha256=None if reaction is None else hashlib.sha256(raw[2]).hexdigest(),
        scene_context_seconds=args.scene_context_seconds,
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
