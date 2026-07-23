#!/usr/bin/env python3
"""Generate deterministic v360 paths for the spherical stabilization gate.

The fixture is deliberately an oracle: a known slow yaw turn is combined with
alternating high-frequency rig shake.  The expected action-natural path keeps
the turn and retains ten percent of the shake.  It validates the contract that
an eventual estimator/optimizer must satisfy; it is not an estimator.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def write_commands(path: Path, rows: list[dict[str, float]], field: str) -> None:
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(f"{row['time_seconds']:.6f} v360 yaw {row[field]:.6f};\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--turn-rate", type=float, default=5.0)
    parser.add_argument("--shake-amplitude", type=float, default=6.0)
    parser.add_argument("--shake-retention", type=float, default=0.1)
    args = parser.parse_args()

    if args.fps <= 0 or args.duration <= 0:
        parser.error("fps and duration must be positive")
    if not 0 <= args.shake_retention <= 1:
        parser.error("shake retention must be between zero and one")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = int(round(args.duration * args.fps))
    rows: list[dict[str, float]] = []
    for index in range(count):
        timestamp = index / args.fps
        intentional = args.turn_rate * timestamp
        shake = args.shake_amplitude if index % 2 == 0 else -args.shake_amplitude
        rows.append(
            {
                "time_seconds": timestamp,
                "intentional_yaw_degrees": intentional,
                "injected_shake_degrees": shake,
                "raw_yaw_degrees": intentional + shake,
                "stabilized_yaw_degrees": intentional + args.shake_retention * shake,
            }
        )

    csv_path = args.output_dir / "known-motion.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    write_commands(args.output_dir / "raw-v360.commands", rows, "raw_yaw_degrees")
    write_commands(
        args.output_dir / "action-natural-v360.commands",
        rows,
        "stabilized_yaw_degrees",
    )

    raw_shake_rms = math.sqrt(
        sum(row["injected_shake_degrees"] ** 2 for row in rows) / len(rows)
    )
    stabilized_shake_rms = raw_shake_rms * args.shake_retention
    manifest = {
        "schema_version": "aegis360.synthetic-spherical-stabilization.v1",
        "fixture_kind": "oracle_known_motion",
        "fps": args.fps,
        "duration_seconds": args.duration,
        "sample_count": count,
        "intentional_turn_rate_degrees_per_second": args.turn_rate,
        "intentional_turn_degrees": rows[-1]["intentional_yaw_degrees"],
        "injected_shake_amplitude_degrees": args.shake_amplitude,
        "action_natural_shake_retention": args.shake_retention,
        "raw_shake_rms_degrees": raw_shake_rms,
        "stabilized_shake_rms_degrees": stabilized_shake_rms,
        "limitations": [
            "Oracle yaw-only fixture; it does not validate visual motion estimation.",
            "Alternating shake is deterministic acceptance evidence, not a comfort model.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
