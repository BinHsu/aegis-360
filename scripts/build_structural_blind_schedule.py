#!/usr/bin/env python3
"""Atomically publish private/public structural blind schedules."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.structural_blind_schedule import (  # noqa: E402
    CONFIG_SHA256, PROOF_SHA256, build_structural_blind_schedule,
    validate_exact_schedule, validate_schedule_config,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection_proof", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--presentation-salt-file", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite output directory")
    try:
        proof_bytes = args.selection_proof.read_bytes()
        config_bytes = args.config.read_bytes()
        salt_bytes = args.presentation_salt_file.read_bytes()
        if hashlib.sha256(proof_bytes).hexdigest() != PROOF_SHA256:
            raise ValueError("selection proof checksum does not match frozen schedule")
        if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
            raise ValueError("schedule config checksum does not match frozen schedule")
        if (len(salt_bytes) != 65 or salt_bytes[-1:] != b"\n"
                or any(byte not in b"0123456789abcdef" for byte in salt_bytes[:-1])
                or stat.S_IMODE(args.presentation_salt_file.stat().st_mode) & 0o077):
            raise ValueError("presentation salt must be one owner-only lowercase 64-hex line")
        proof, config = json.loads(proof_bytes), json.loads(config_bytes)
        validate_schedule_config(config)
        inputs = dict(selection_proof=proof, selection_proof_sha256=PROOF_SHA256,
                      config=config, config_sha256=CONFIG_SHA256,
                      presentation_salt_hex=salt_bytes[:-1].decode("ascii"))
        private, public = build_structural_blind_schedule(**inputs)
        validate_exact_schedule(private, public, **inputs)
    except (OSError, json.JSONDecodeError, UnicodeError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) else "input could not be read"
        parser.error(message)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=args.output.parent))
    try:
        (stage / "private-schedule.json").write_text(json.dumps(private, allow_nan=False, indent=2, sort_keys=True) + "\n")
        (stage / "public-reviewer-index.json").write_text(json.dumps(public, allow_nan=False, indent=2, sort_keys=True) + "\n")
        os.rename(stage, args.output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print(json.dumps({"packet_count": 8}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
