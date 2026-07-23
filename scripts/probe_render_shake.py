#!/usr/bin/env python3
"""Compare dependency-light screen-space shake proxies in flat video renders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.shake_metrics import motion_samples, summarize_samples  # noqa: E402


def decode_gray_frames(path: Path, width: int, height: int, fps: float):
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-an", "-vf", f"fps={fps},scale={width}:{height}:flags=area,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None
    frame_bytes = width * height
    try:
        while True:
            frame = process.stdout.read(frame_bytes)
            if not frame:
                break
            if len(frame) != frame_bytes:
                raise RuntimeError(f"FFmpeg returned a truncated frame for {path}")
            yield frame
    finally:
        process.stdout.close()
        return_code = process.wait()
        if return_code:
            raise RuntimeError(f"FFmpeg failed for {path} with exit code {return_code}")


def parse_input(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("input must be LABEL=VIDEO")
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise argparse.ArgumentTypeError("input must be LABEL=VIDEO")
    path = Path(raw_path)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"video does not exist: {path}")
    return label, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=parse_input, metavar="LABEL=VIDEO")
    parser.add_argument("--fps", type=float, default=6.0)
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=90)
    parser.add_argument("--search-radius", type=int, default=8)
    parser.add_argument("--pixel-stride", type=int, default=2)
    parser.add_argument("--segment-fraction", type=float, default=0.2)
    args = parser.parse_args()
    if args.fps <= 0:
        parser.error("--fps must be positive")

    reports = {}
    for label, path in args.inputs:
        if label in reports:
            parser.error(f"duplicate input label: {label}")
        samples = motion_samples(
            decode_gray_frames(path, args.width, args.height, args.fps),
            args.width,
            args.height,
            args.fps,
            search_radius=args.search_radius,
            pixel_stride=args.pixel_stride,
        )
        reports[label] = {
            "input_filename": path.name,
            **summarize_samples(
                samples, args.width, segment_fraction=args.segment_fraction
            ),
        }
    print(json.dumps({
        "schema_version": 1,
        "metric": "downscaled_gray_global_translation_block_match",
        "configuration": {
            "fps": args.fps,
            "width": args.width,
            "height": args.height,
            "search_radius": args.search_radius,
            "pixel_stride": args.pixel_stride,
            "segment_fraction": args.segment_fraction,
        },
        "renders": reports,
        "limitations": [
            "Screen-space proxy: subject motion and parallax are not camera shake.",
            "Translation-only: roll and perspective/rotation are not estimated.",
            "Motion beyond search_radius is clipped or may be mismatched.",
            "Compare renders of the same source, interval, resolution, and FOV.",
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
