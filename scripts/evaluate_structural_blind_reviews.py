#!/usr/bin/env python3
"""Validate frozen blind-review inputs and atomically publish their evaluation."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.structural_blind_coordinator import (  # noqa: E402
    coordinate_structural_blind_evaluation, write_json_no_overwrite,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "proof", "private_schedule", "public_index", "bundle_directory",
                 "salt", "review_a", "review_b", "scores", "attestation", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        result = coordinate_structural_blind_evaluation(
            config_path=args.config, proof_path=args.proof,
            private_schedule_path=args.private_schedule, public_index_path=args.public_index,
            bundle_directory=args.bundle_directory, salt_path=args.salt,
            review_a_path=args.review_a, review_b_path=args.review_b,
            score_path=args.scores, attestation_path=args.attestation)
        write_json_no_overwrite(args.output, result)
    except (OSError, ValueError) as error:
        parser.error(str(error) if isinstance(error, ValueError) else "output could not be written")
    print(json.dumps({"outcome": result["evaluation"]["gate"]["outcome"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
