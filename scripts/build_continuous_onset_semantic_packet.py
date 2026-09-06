#!/usr/bin/env python3
"""Build one atomic pixel-free continuous-onset semantic packet."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.continuous_onset_semantic_packet import build_continuous_onset_semantic_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("onset_json", type=Path)
    parser.add_argument("samples_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("candidate_id")
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    paths = (args.onset_json, args.samples_json, args.grid_json)
    if not all(path.is_file() for path in paths):
        parser.error("required input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raws = [path.read_bytes() for path in paths]
    document = build_continuous_onset_semantic_packet(
        *[json.loads(raw) for raw in raws], candidate_id=args.candidate_id,
        onset_sha256=hashlib.sha256(raws[0]).hexdigest(),
        samples_sha256=hashlib.sha256(raws[1]).hexdigest(),
        grid_sha256=hashlib.sha256(raws[2]).hexdigest(),
    )
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
