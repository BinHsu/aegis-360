#!/usr/bin/env python3
"""Build the frozen direct-source structural chapter contrast artifact."""

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
from aegis360.structural_chapter_labeled_contrast import (  # noqa: E402
    build_artifact, run_episode_audit, sample_plan, validate_artifact,
    validate_config, validate_evidence,
)

FROZEN_CONFIG_SHA256 = "8baf66a00a008625cd91292aaa8ac0a8794d9fb20338e0acfab054b3a2f7f7a2"


def read_json(path: Path):
    data = path.read_bytes()
    return data, json.loads(data)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def fail(parser, message):
    parser.error(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--binding", nargs=4, action="append", metavar=("EVENT", "PACKET", "LABEL", "SEMANTICS"), required=True)
    args = parser.parse_args()
    if args.output.exists():
        fail(parser, "refusing to overwrite output")
    try:
        config_bytes, config = read_json(args.config)
        fixture_bytes, fixtures = read_json(args.fixtures)
        validate_config(config)
        if hashlib.sha256(config_bytes).hexdigest() != FROZEN_CONFIG_SHA256:
            raise ValueError("config checksum does not match frozen contract")
        if hashlib.sha256(fixture_bytes).hexdigest() != config["episode_audit"]["fixture_sha256"]:
            raise ValueError("fixture checksum does not match frozen config")
        episode_results = run_episode_audit(fixtures)
        bindings = {}
        for event_id, packet_name, label_name, semantics_name in args.binding:
            if event_id in bindings:
                raise ValueError("duplicate evidence binding")
            packet_bytes, packet = read_json(Path(packet_name))
            label_bytes, label = read_json(Path(label_name))
            semantics_bytes, semantics = read_json(Path(semantics_name))
            bindings[event_id] = (packet_bytes, packet, label_bytes, label, semantics_bytes, semantics)
        validate_evidence(config, bindings)
        before = digest(args.source)
        if before != config["source"]["sha256"]:
            raise ValueError("source checksum does not match frozen config")
        wanted = {row["frame_index"] for rows in sample_plan(config).values() for row in rows}
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-threads", "2", "-i", str(args.source), "-map", "0:v:0", "-an", "-vf", "fps=fps=2:start_time=0:round=near,scale=160:80:flags=area,format=gray", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        assert process.stdout is not None
        selected = {}; count = 0; frame_bytes = 160 * 80
        while True:
            frame = process.stdout.read(frame_bytes)
            if not frame:
                break
            if len(frame) != frame_bytes:
                raise ValueError("decoded stream ended with a partial frame")
            if count in wanted:
                selected[count] = frame
            count += 1
        if process.wait() != 0:
            raise ValueError("FFmpeg decode failed")
        after = digest(args.source)
        artifact = build_artifact(config=config, config_sha256=hashlib.sha256(config_bytes).hexdigest(), fixture_sha256=hashlib.sha256(fixture_bytes).hexdigest(), source_sha256_before=before, source_sha256_after=after, frame_count=count, selected_frames=selected, episode_results=episode_results)
        validate_artifact(artifact, config=config, config_sha256=hashlib.sha256(config_bytes).hexdigest(), fixture_sha256=hashlib.sha256(fixture_bytes).hexdigest(), source_sha256_before=before, source_sha256_after=after, frame_count=count, selected_frames=selected, episode_results=episode_results)
        payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, prefix=f".{args.output.name}.", suffix=".tmp", delete=False) as stage:
            stage.write(payload); stage_name = stage.name
        try:
            os.link(stage_name, args.output)
        finally:
            Path(stage_name).unlink(missing_ok=True)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        if "process" in locals() and process.poll() is None:
            process.kill(); process.wait()
        # Contract errors are deliberately path-free; OS/JSON messages may
        # contain private local filenames and are therefore not forwarded.
        message = str(error) if isinstance(error, ValueError) else "input or output could not be read"
        fail(parser, message)
    except BaseException:
        if "process" in locals():
            process.kill(); process.wait()
        raise
    print(json.dumps({"frame_count": count, "primary_passed": artifact["gate"]["primary_passed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
