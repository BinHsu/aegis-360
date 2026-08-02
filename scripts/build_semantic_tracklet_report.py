#!/usr/bin/env python3
"""Build an atomic framing-filtered ambiguity-aware tracklet diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_quality import filter_subject_framing_events  # noqa: E402
from aegis360.semantic_spherical import semantic_events_to_spherical_results  # noqa: E402
from aegis360.semantic_tracklets import build_semantic_tracklet_diagnostic  # noqa: E402
from aegis360.spherical_dedup import deduplicate_spherical_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if not args.events_json.is_file():
        parser.error("events JSON is missing")
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    document = json.loads(args.events_json.read_text(encoding="utf-8"))
    accepted, quality = filter_subject_framing_events(document)
    results = tuple(
        deduplicate_spherical_candidates(result).result
        for result in semantic_events_to_spherical_results(accepted)
    )
    tracklets = build_semantic_tracklet_diagnostic(results)
    artifact = {
        "schema_version": "aegis360.semantic-tracklet-report.v1",
        "source_id": document["source_id"],
        "model_id": document["model_id"],
        "quality": quality,
        "tracklets": tracklets,
        "privacy": tracklets["privacy"],
    }
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.",
        dir=args.output_directory.parent,
    ))
    try:
        (staging / "tracklets.json").write_text(
            json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({
        "accepted": quality["accepted_detection_count"],
        "quarantined": quality["quarantined_detection_count"],
        "acquisitions": len(tracklets["acquisitions"]),
        "terminations": len(tracklets["terminations"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
