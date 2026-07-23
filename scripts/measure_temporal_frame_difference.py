#!/usr/bin/env python3
"""Measure mean absolute luma change between adjacent decoded video frames."""

from __future__ import annotations

import argparse
import json
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("--width", type=int, required=True)
parser.add_argument("--height", type=int, required=True)
args = parser.parse_args()

if args.width <= 0 or args.height <= 0:
    parser.error("width and height must be positive")

frame_size = args.width * args.height
process = subprocess.Popen(
    [
        "ffmpeg", "-v", "error", "-i", args.input,
        "-vf", f"scale={args.width}:{args.height},format=gray",
        "-f", "rawvideo", "-",
    ],
    stdout=subprocess.PIPE,
)
assert process.stdout is not None

prior: bytes | None = None
pair_means: list[float] = []
while True:
    frame = process.stdout.read(frame_size)
    if not frame:
        break
    if len(frame) != frame_size:
        process.kill()
        raise SystemExit("decoder returned a partial frame")
    if prior is not None:
        pair_means.append(
            sum(abs(current - previous) for current, previous in zip(frame, prior))
            / frame_size
        )
    prior = frame

return_code = process.wait()
if return_code:
    raise SystemExit(f"ffmpeg decoder failed with status {return_code}")
if not pair_means:
    raise SystemExit("at least two decoded frames are required")

print(json.dumps({
    "schemaVersion": 1,
    "metric": "adjacent_mean_absolute_luma_difference",
    "frameWidth": args.width,
    "frameHeight": args.height,
    "framePairCount": len(pair_means),
    "mean": sum(pair_means) / len(pair_means),
    "maximum": max(pair_means),
}, sort_keys=True))
