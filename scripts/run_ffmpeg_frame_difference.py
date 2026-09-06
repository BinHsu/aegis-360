#!/usr/bin/env python3
"""Acquire bounded frame-difference metadata into one atomic path-free artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.frame_difference_samples import (  # noqa: E402
    build_frame_difference_samples, validate_frame_difference_acquisition_config,
)


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
    parser.add_argument("acquisition_config", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()
    if not args.source_video.is_file():
        parser.error("source video is missing")
    if not args.acquisition_config.is_file():
        parser.error("acquisition config is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if (not math.isfinite(args.start) or args.start < 0
            or not math.isfinite(args.duration) or args.duration <= 0):
        parser.error("start and duration must be finite and bounded")
    config_raw = args.acquisition_config.read_bytes()
    config = json.loads(config_raw)
    # The builder validates the complete v2 config. Read only after validation
    # would require metadata, so reject the schema here and let it enforce all
    # remaining exact fields on artifact construction.
    if config.get("schema_version") != "aegis360.frame-difference-acquisition-config.v2":
        parser.error("runner requires acquisition config v2")
    try:
        validate_frame_difference_acquisition_config(config)
    except ValueError as error:
        parser.error(str(error))
    fps = config.get("sample_fps")
    width = config.get("proxy_width")
    threads = config.get("ffmpeg_threads")
    filter_graph = (
        f"fps=fps={fps},scale=w={width}:h=-2,format=pix_fmts=gray,"
        "tblend=all_mode=difference,signalstats,"
        "metadata=mode=print:key=lavfi.signalstats.YAVG:file=-"
    )
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-threads", str(threads), "-ss", str(args.start), "-t",
        str(args.duration), "-i", str(args.source_video), "-vf", filter_graph,
        "-an", "-f", "null", "-",
    ]
    source_sha256 = sha256_file(args.source_video)
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    if sha256_file(args.source_video) != source_sha256:
        parser.error("source video changed during acquisition")
    artifact = build_frame_difference_samples(
        source_id=args.source_id,
        window={"start_seconds": args.start, "duration_seconds": args.duration},
        source_sha256=source_sha256, config=config,
        config_sha256=hashlib.sha256(config_raw).hexdigest(),
        metadata_text=completed.stdout,
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
    print(json.dumps({"sample_count": len(artifact["samples"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
