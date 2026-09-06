#!/usr/bin/env python3
"""Acquire and atomically publish eight frozen label-free structural scores."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.structural_label_free_scores import (  # noqa: E402
    PROOF_SHA256, SOURCE_SHA256, build_score_artifact, sample_plan,
    validate_score_artifact, validate_score_contract,
)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""): value.update(chunk)
    return value.hexdigest()


def strict(path):
    def reject(value): raise ValueError("JSON contains a non-finite number")
    def closed(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("JSON contains a duplicate key")
            result[key] = value
        return result
    return json.loads(path.read_bytes().decode("utf-8"), parse_constant=reject,
                      object_pairs_hook=closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path); parser.add_argument("selection_proof", type=Path)
    parser.add_argument("score_contract", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists(): parser.error("refusing to overwrite output")
    process = None
    try:
        if digest(args.source) != SOURCE_SHA256 or digest(args.selection_proof) != PROOF_SHA256:
            raise ValueError("source or selection proof checksum does not match")
        proof, contract = strict(args.selection_proof), strict(args.score_contract)
        validate_score_contract(contract)
        plan = sample_plan(proof, contract)
        wanted = {index for _, indices in plan for index in indices}
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-threads", "2", "-i", str(args.source), "-map", "0:v:0", "-an", "-vf", "fps=fps=2:start_time=0:round=near,scale=160:80:flags=area,format=gray", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE); selected = {}; count = 0
        assert process.stdout is not None
        while True:
            frame = process.stdout.read(160 * 80)
            if not frame: break
            if len(frame) != 160 * 80: raise ValueError("decoded stream ended with a partial frame")
            if count in wanted: selected[count] = frame
            count += 1
        if process.wait() != 0: raise ValueError("FFmpeg score acquisition failed")
        after = digest(args.source)
        inputs = dict(contract=contract, selection_proof=proof,
            selection_proof_sha256=PROOF_SHA256, source_sha256_before=SOURCE_SHA256,
            source_sha256_after=after, frame_count=count, selected_frames=selected)
        artifact = build_score_artifact(**inputs); validate_score_artifact(artifact, **inputs)
        payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, prefix=f".{args.output.name}.", delete=False) as stage:
            stage.write(payload); stage_name = stage.name
        try: os.link(stage_name, args.output)
        finally: Path(stage_name).unlink(missing_ok=True)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        if process is not None and process.poll() is None: process.kill(); process.wait()
        parser.error(str(error) if isinstance(error, ValueError) else "score input or output failed")
    print(json.dumps({"score_count": 8}, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
