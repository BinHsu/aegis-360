#!/usr/bin/env python3
"""Build review-only continuous-onset candidates from exact samples."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.continuous_onset_candidates import build_continuous_onset_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.samples_json.is_file() or not args.policy_json.is_file():
        parser.error("samples or policy is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    samples_raw = args.samples_json.read_bytes()
    policy_raw = args.policy_json.read_bytes()
    artifact = build_continuous_onset_candidates(
        json.loads(samples_raw), json.loads(policy_raw),
        samples_sha256=hashlib.sha256(samples_raw).hexdigest(),
        policy_sha256=hashlib.sha256(policy_raw).hexdigest(),
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
    print(json.dumps({"candidate_count": len(artifact["candidates"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
