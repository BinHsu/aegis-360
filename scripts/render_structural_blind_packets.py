#!/usr/bin/env python3
"""Render and atomically publish a structural blind-review bundle."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.structural_blind_renderer import render_structural_blind_bundle  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("private_schedule", "public_index", "selection_proof", "config",
                 "presentation_salt", "render_media", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--private-schedule-sha256", required=True)
    parser.add_argument("--public-index-sha256", required=True)
    parser.add_argument("--render-media-sha256", required=True)
    args = parser.parse_args()
    try:
        result = render_structural_blind_bundle(
            private_schedule_path=args.private_schedule,
            private_schedule_sha256=args.private_schedule_sha256,
            public_index_path=args.public_index,
            public_index_sha256=args.public_index_sha256,
            selection_proof_path=args.selection_proof, config_path=args.config,
            presentation_salt_path=args.presentation_salt,
            render_media_path=args.render_media,
            render_media_sha256=args.render_media_sha256,
            output_directory=args.output)
    except (OSError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) else "render input or output failed"
        parser.error(message)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
