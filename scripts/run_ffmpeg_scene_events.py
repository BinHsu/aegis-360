#!/usr/bin/env python3
"""Run bounded proxy scene-change analysis and write one atomic artifact."""

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
from aegis360.scene_events import build_scene_events  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("source_id")
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--sample-fps", type=float, default=10.0)
    parser.add_argument("--proxy-width", type=int, default=320)
    args = parser.parse_args()
    if not args.source_video.is_file():
        parser.error("source video is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    version = subprocess.run(
        ["ffmpeg", "-version"], check=True, capture_output=True, text=True,
    ).stdout.splitlines()[0]
    filter_graph = (
        f"fps={args.sample_fps},scale={args.proxy_width}:-2,"
        f"select='gt(scene,{args.threshold})',metadata=print:file=-"
    )
    completed = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-threads", "2",
        "-i", str(args.source_video), "-vf", filter_graph, "-an", "-f", "null", "-",
    ], check=True, capture_output=True, text=True)
    artifact = build_scene_events(
        source_id=args.source_id, source_sha256=sha256_file(args.source_video),
        threshold=args.threshold, sample_fps=args.sample_fps,
        proxy_width=args.proxy_width, ffmpeg_version=version,
        metadata_output=completed.stdout,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.output_json.parent,
        prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
    ) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"event_count": len(artifact["events"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
