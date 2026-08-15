#!/usr/bin/env python3
"""Render sparse review frames, run one adapter, then always delete frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.event_review_packet import validate_event_review_packet  # noqa: E402
from aegis360.review_media import (  # noqa: E402
    build_review_render_jobs,
    build_transient_media_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("timeline_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("packet_json", type=Path)
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=216)
    parser.add_argument("adapter_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not all(path.is_file() for path in (
        args.source_video, args.timeline_json, args.grid_json, args.packet_json,
    )):
        parser.error("source or evidence is missing")
    if not args.adapter_command:
        parser.error("adapter command is required after --")
    command = args.adapter_command[1:] if args.adapter_command[0] == "--" else args.adapter_command
    if not command:
        parser.error("adapter command is empty")
    timeline_bytes = args.timeline_json.read_bytes()
    grid_bytes = args.grid_json.read_bytes()
    packet = json.loads(args.packet_json.read_bytes())
    timeline = json.loads(timeline_bytes)
    grid = json.loads(grid_bytes)
    validate_event_review_packet(
        packet, timeline, grid,
        timeline_sha256=hashlib.sha256(timeline_bytes).hexdigest(),
        grid_sha256=hashlib.sha256(grid_bytes).hexdigest(),
    )
    jobs = build_review_render_jobs(packet, grid, width=args.width, height=args.height)
    with tempfile.TemporaryDirectory(prefix="aegis-event-review.") as temporary:
        work = Path(temporary)
        for job in jobs:
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(job["timestamp_seconds"]), "-i", str(args.source_video),
                "-frames:v", "1", "-vf",
                "v360=input=equirect:output=flat:"
                f"w={job['width']}:h={job['height']}:yaw={job['yaw_degrees']}:"
                f"pitch={job['pitch_degrees']}:h_fov={job['horizontal_fov_degrees']}:"
                "interp=linear",
                "-an", str(work / job["filename"]),
            ], check=True)
        index_path = work / "index.json"
        index_path.write_text(
            json.dumps(build_transient_media_index(packet, jobs), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["AEGIS_REVIEW_MEDIA_DIR"] = str(work)
        environment["AEGIS_REVIEW_MEDIA_INDEX"] = str(index_path)
        completed = subprocess.run(command, cwd=work, env=environment, check=False)
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
