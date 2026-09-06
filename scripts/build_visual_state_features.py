#!/usr/bin/env python3
"""Stream deterministic visual-state features from a canonical proxy bundle."""

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
from aegis360.analysis_proxy_bundle import validate_analysis_proxy_config  # noqa: E402
from aegis360.visual_state_features import (  # noqa: E402
    build_visual_state_features, expected_sample_count,
    validate_proxy_bundle_for_features, validate_visual_state_config,
    validate_visual_state_feature_document,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proxy_bundle", type=Path)
    parser.add_argument("proxy_config", type=Path)
    parser.add_argument("feature_config", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    manifest_path = args.proxy_bundle / "manifest.json"
    proxy_path = args.proxy_bundle / "analysis-proxy.mkv"
    if not manifest_path.is_file() or not proxy_path.is_file():
        parser.error("canonical proxy bundle is incomplete")
    if not args.proxy_config.is_file() or not args.feature_config.is_file():
        parser.error("required config is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    try:
        manifest = json.loads(manifest_path.read_text())
        proxy_config_bytes = args.proxy_config.read_bytes()
        proxy_config = json.loads(proxy_config_bytes)
        validate_analysis_proxy_config(proxy_config)
        feature_config_bytes = args.feature_config.read_bytes()
        feature_config = json.loads(feature_config_bytes)
        validate_visual_state_config(feature_config)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    proxy_hash = sha256_file(proxy_path)
    proxy_config_hash = hashlib.sha256(proxy_config_bytes).hexdigest()
    try:
        validate_proxy_bundle_for_features(
            manifest, proxy_sha256=proxy_hash,
            proxy_config_sha256=proxy_config_hash,
        )
    except ValueError as error:
        parser.error(str(error))
    expected = expected_sample_count(manifest["probe"]["duration_seconds"])
    frame_bytes = feature_config["frame_width"] * feature_config["frame_height"] * 3
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-threads", str(feature_config["decoder_threads"]), "-i", str(proxy_path),
        "-map", "0:v:0", "-an", "-vf",
        "fps=1/1,scale=96:48:flags=area,format=rgb24",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None

    def frames():
        while True:
            frame = process.stdout.read(frame_bytes)
            if not frame:
                return
            if len(frame) != frame_bytes:
                raise ValueError("decoded stream ended with a partial RGB frame")
            yield frame

    try:
        artifact = build_visual_state_features(
            bundle=manifest, proxy_sha256=proxy_hash,
            proxy_config_sha256=proxy_config_hash,
            config=feature_config,
            config_sha256=hashlib.sha256(feature_config_bytes).hexdigest(),
            frames=frames(), frame_count=expected,
        )
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg exited with status {return_code}")
        if sha256_file(proxy_path) != proxy_hash:
            raise RuntimeError("analysis proxy changed during feature acquisition")
        validate_visual_state_feature_document(artifact)
        payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
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
    except BaseException:
        process.kill()
        process.wait()
        raise
    print(json.dumps({"sample_count": expected}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
