#!/usr/bin/env python3
"""Validate the benchmark duration ladder against the asset manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import tomllib


EXPECTED_DURATIONS = [30, 60, 180, 300]
EXPECTED_OUTPUTS = ["fixed-forward", "auto-directed", "debug-overlay"]


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate(manifest: dict, ladder: dict) -> list[str]:
    errors: list[str] = []
    durations = ladder.get("duration_seconds")
    if durations != EXPECTED_DURATIONS:
        errors.append(
            f"duration_seconds must be {EXPECTED_DURATIONS}, got {durations!r}"
        )
    outputs = ladder.get("required_outputs")
    if outputs != EXPECTED_OUTPUTS:
        errors.append(f"required_outputs must be {EXPECTED_OUTPUTS}, got {outputs!r}")

    for flag in (
        "same_start_required",
        "same_configuration_required",
        "debug_uses_auto_path",
    ):
        if ladder.get(flag) is not True:
            errors.append(f"{flag} must be true")

    start = ladder.get("start_seconds")
    if not isinstance(start, (int, float)) or start < 0:
        errors.append(f"start_seconds must be non-negative, got {start!r}")
        start = 0

    source_assets = {asset["id"]: asset for asset in manifest.get("asset", [])}
    ladder_assets = {asset["id"]: asset for asset in ladder.get("asset", [])}
    if set(ladder_assets) != set(source_assets):
        errors.append(
            "ladder asset ids must exactly match benchmark manifest asset ids"
        )

    for asset_id, source in source_assets.items():
        if asset_id not in ladder_assets:
            continue
        available = source["reported_duration_seconds"] - start
        expected = [duration for duration in EXPECTED_DURATIONS if duration <= available]
        enabled = ladder_assets[asset_id].get("enabled_duration_seconds")
        if enabled != expected:
            errors.append(
                f"{asset_id}: enabled_duration_seconds must be {expected} "
                f"for {available:.3f}s available, got {enabled!r}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ladder", nargs="?", type=Path, default=Path("benchmarks/duration-ladder.toml")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("benchmarks/manifest.toml")
    )
    args = parser.parse_args()
    errors = validate(load_toml(args.manifest), load_toml(args.ladder))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("duration ladder contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
