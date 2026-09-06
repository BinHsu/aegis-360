#!/usr/bin/env python3
"""Build atomic review-only chapter proposals from visual-state JSON."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.chapter_proposal_candidates import (  # noqa: E402
    build_chapter_proposal_candidates,
    validate_chapter_proposal_config,
    validate_chapter_proposal_document,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("visual_state_json", type=Path)
    parser.add_argument("config_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.visual_state_json.is_file() or not args.config_json.is_file():
        parser.error("required input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")

    try:
        feature_bytes = args.visual_state_json.read_bytes()
        config_bytes = args.config_json.read_bytes()
        features = json.loads(feature_bytes)
        config = json.loads(config_bytes)
        validate_chapter_proposal_config(config)
        inputs = {
            "visual_state_features": features,
            "visual_state_features_sha256": hashlib.sha256(feature_bytes).hexdigest(),
            "config": config,
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        }
        document = build_chapter_proposal_candidates(**inputs)
        validate_chapter_proposal_document(document, **inputs)
        payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=args.output_json.parent,
            prefix=f".{args.output_json.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.link(temporary_name, args.output_json)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
