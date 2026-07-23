#!/usr/bin/env python3
"""Orchestrate one bounded auto-directed slice from Vision sequence JSON."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.slice_orchestrator import run_slice  # noqa: E402
from aegis360.greedy_config import load_greedy_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vision_json", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--start", required=True, type=float)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "greedy-first-slice-v1.toml",
    )
    parser.add_argument("--render-adapter", type=Path)
    parser.add_argument("--source-media", type=Path)
    args = parser.parse_args()
    try:
        run_slice(
            args.vision_json.read_text(encoding="utf-8"),
            args.output_dir,
            source_id=args.source_id,
            width=args.width,
            height=args.height,
            start_seconds=args.start,
            duration_seconds=args.duration,
            slice_config=load_greedy_config(args.config),
            render_adapter=args.render_adapter,
            source_media=args.source_media,
        )
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(f"bundle={args.output_dir}")


if __name__ == "__main__":
    main()
