#!/usr/bin/env python3
"""Atomically create private and public blind chapter-review schedules."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.blind_chapter_review_schedule import (  # noqa: E402
    build_blind_chapter_review_schedule, validate_schedule_config,
    validate_exact_blind_chapter_review_schedule)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--proposals-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--presentation-salt-file", required=True, type=Path,
                        help="private file containing exactly one lowercase 64-hex line")
    args = parser.parse_args()
    if not args.proposals.is_file() or not args.config.is_file():
        parser.error("required input is missing")
    if args.output.exists():
        parser.error("refusing to overwrite output directory")
    try:
        if not args.presentation_salt_file.is_file():
            raise ValueError("presentation salt file is missing")
        salt_bytes = args.presentation_salt_file.read_bytes()
        if (len(salt_bytes) != 65 or salt_bytes[-1:] != b"\n"
                or any(byte not in b"0123456789abcdef" for byte in salt_bytes[:-1])):
            raise ValueError("presentation salt file must contain exactly one lowercase 64-hex line")
        presentation_salt_hex = salt_bytes[:-1].decode("ascii")
        proposal_bytes = args.proposals.read_bytes()
        if sha(proposal_bytes) != args.proposals_sha256:
            raise ValueError("chapter proposal file hash does not match")
        proposals = json.loads(proposal_bytes)
        config_bytes = args.config.read_bytes()
        config = json.loads(config_bytes)
        validate_schedule_config(config)
        private, public = build_blind_chapter_review_schedule(
            proposals=proposals, proposals_sha256=args.proposals_sha256,
            source_sha256=args.source_sha256, policy_sha256=args.policy_sha256,
            protocol_sha256=args.protocol_sha256, config=config,
            config_sha256=sha(config_bytes),
            presentation_salt_hex=presentation_salt_hex)
        validate_exact_blind_chapter_review_schedule(
            private, public, proposals=proposals,
            proposals_sha256=args.proposals_sha256,
            source_sha256=args.source_sha256,
            policy_sha256=args.policy_sha256,
            protocol_sha256=args.protocol_sha256, config=config,
            config_sha256=sha(config_bytes),
            presentation_salt_hex=presentation_salt_hex)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=args.output.parent))
    try:
        (stage / "private-schedule.json").write_text(
            json.dumps(private, allow_nan=False, indent=2, sort_keys=True) + "\n")
        (stage / "public-reviewer-index.json").write_text(
            json.dumps(public, allow_nan=False, indent=2, sort_keys=True) + "\n")
        os.rename(stage, args.output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print(json.dumps({"packet_count": len(public["packets"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
