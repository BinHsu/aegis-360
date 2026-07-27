#!/usr/bin/env python3
"""Assemble privacy-safe independent Vision tile registration evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_failure(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if SAFE_ID.fullmatch(text) else "backend_error"


def assemble(manifest: dict, manifest_directory: Path) -> dict:
    required = {
        "sourceId", "viewportId", "parentWidth", "parentHeight", "tiles"
    }
    if set(manifest) != required:
        raise ValueError("manifest fields do not match the tile schema")
    if not SAFE_ID.fullmatch(manifest["sourceId"]):
        raise ValueError("sourceId must be privacy-safe")
    if not SAFE_ID.fullmatch(manifest["viewportId"]):
        raise ValueError("viewportId must be privacy-safe")
    parent_width = manifest["parentWidth"]
    parent_height = manifest["parentHeight"]
    if (
        not isinstance(parent_width, int) or parent_width <= 0
        or not isinstance(parent_height, int) or parent_height <= 0
    ):
        raise ValueError("parent dimensions must be positive integers")
    if not isinstance(manifest["tiles"], list) or not manifest["tiles"]:
        raise ValueError("at least one tile is required")

    tile_ids = [item.get("id") for item in manifest["tiles"]]
    if (
        any(not isinstance(item, str) or not SAFE_ID.fullmatch(item)
            for item in tile_ids)
        or len(set(tile_ids)) != len(tile_ids)
    ):
        raise ValueError("tile IDs must be privacy-safe and unique")

    sequences = []
    reference_timing = None
    for item in manifest["tiles"]:
        if set(item) != {"id", "x", "y", "width", "height", "evidenceFile"}:
            raise ValueError("tile fields do not match the tile schema")
        extent = tuple(item[key] for key in ("x", "y", "width", "height"))
        if any(not isinstance(value, int) for value in extent):
            raise ValueError("tile extent must contain integers")
        x, y, width, height = extent
        if (
            x < 0 or y < 0 or width <= 0 or height <= 0
            or x + width > parent_width or y + height > parent_height
        ):
            raise ValueError("tile must lie inside the parent viewport")

        evidence_path = (manifest_directory / item["evidenceFile"]).resolve()
        evidence = load(evidence_path)
        if (
            evidence.get("frameWidth") != width
            or evidence.get("frameHeight") != height
        ):
            raise ValueError("tile evidence dimensions disagree with manifest")
        observations = evidence.get("observations")
        if not isinstance(observations, list) or len(observations) < 2:
            raise ValueError("tile evidence must contain at least two frames")
        timing = [
            (row.get("frameIndex"), row.get("timestampSeconds"))
            for row in observations
        ]
        if reference_timing is None:
            reference_timing = timing
        elif timing != reference_timing:
            raise ValueError("tile evidence timestamps disagree")

        safe_rows = []
        for row in observations:
            frame_index = row.get("frameIndex")
            timestamp = row.get("timestampSeconds")
            state = row.get("state")
            homography = row.get("homographyRowMajor")
            if (
                not isinstance(frame_index, int)
                or not isinstance(timestamp, (int, float))
                or not math.isfinite(timestamp)
                or state not in {"reference", "measured", "error"}
            ):
                raise ValueError("invalid tile observation")
            if state == "measured" and (
                not isinstance(homography, list)
                or len(homography) != 9
                or not all(
                    isinstance(value, (int, float)) and math.isfinite(value)
                    for value in homography
                )
            ):
                raise ValueError("measured tile observation needs a homography")
            safe_rows.append({
                "frame_index": frame_index,
                "timestamp_seconds": timestamp,
                "state": state,
                "homography_row_major": homography if state == "measured" else None,
                "failure_reason": safe_failure(row.get("error")),
            })
        sequences.append({
            "tile_id": item["id"],
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "observations": safe_rows,
        })

    return {
        "schema_version": "aegis360.vision-tile-evidence.v1",
        "source_id": manifest["sourceId"],
        "viewport_id": manifest["viewportId"],
        "parent_width": parent_width,
        "parent_height": parent_height,
        "tile_sequences": sequences,
        "provenance": {
            "adapter_id": "aegis.vision-tile-evidence-assembler",
            "backend_id": "VNTrackHomographicImageRegistrationRequest",
            "registration_scope": "independent-tile-sequences",
        },
        "privacy": {
            "contains_source_paths": False,
            "contains_pixels": False,
            "contains_identity_data": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit("refusing to overwrite output")
    result = assemble(load(arguments.manifest), arguments.manifest.parent)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
