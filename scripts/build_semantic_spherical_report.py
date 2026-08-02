#!/usr/bin/env python3
"""Convert v2 semantic events to an atomic path-free spherical dedup report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_spherical import build_semantic_spherical_artifact  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if not args.events_json.is_file():
        parser.error("events JSON is missing")
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    document = json.loads(args.events_json.read_text(encoding="utf-8"))
    artifact = build_semantic_spherical_artifact(document)
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.",
        dir=args.output_directory.parent,
    ))
    try:
        (staging / "spherical-dedup.json").write_text(
            json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps(artifact["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
