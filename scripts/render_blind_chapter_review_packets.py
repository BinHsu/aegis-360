#!/usr/bin/env python3
"""Atomically render a neutral transient blind chapter-review bundle."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.blind_chapter_review_renderer import (  # noqa: E402
    render_blind_chapter_review_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_schedule", type=Path)
    parser.add_argument("public_index", type=Path)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("presentation_salt_file", type=Path)
    parser.add_argument("render_media", type=Path,
                        help="canonical proxy using the schedule proxy timebase")
    parser.add_argument("output", type=Path)
    parser.add_argument("--proposals-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--render-media-sha256", required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--panel-width", type=int, default=480)
    parser.add_argument("--panel-height", type=int, default=270)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    try:
        result = render_blind_chapter_review_bundle(
            private_schedule_path=args.private_schedule,
            public_index_path=args.public_index, proposals_path=args.proposals,
            config_path=args.config,
            presentation_salt_path=args.presentation_salt_file,
            render_media_path=args.render_media, output_directory=args.output,
            proposals_sha256=args.proposals_sha256, source_sha256=args.source_sha256,
            render_media_sha256=args.render_media_sha256,
            policy_sha256=args.policy_sha256, protocol_sha256=args.protocol_sha256,
            panel_width=args.panel_width, panel_height=args.panel_height,
            ffmpeg=args.ffmpeg,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
