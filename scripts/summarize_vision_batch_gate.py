#!/usr/bin/env python3
"""Aggregate privacy-safe summaries from a Vision frame-gate batch."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


RSS_PATTERN = re.compile(r"(\d+)\s+maximum resident set size")
ELAPSED_PATTERN = re.compile(r"([0-9.]+)\s+real")


def _metric(pattern: re.Pattern[str], text: str, convert):
    match = pattern.search(text)
    return convert(match.group(1)) if match else None


def summarize(sample_dirs: list[Path], expected_source_id: str) -> dict:
    samples = []
    totals: dict[str, int] = {}
    request_errors: dict[str, int] = {}
    for sample_dir in sample_dirs:
        evidence_path = sample_dir / "vision-frame-gate.json"
        metrics_path = sample_dir / "vision-frame-gate.metrics.txt"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        metrics = metrics_path.read_text(encoding="utf-8")
        frames = evidence["frames"]
        source_ids = {frame["sourceId"] for frame in frames}
        if source_ids != {expected_source_id}:
            raise ValueError(
                f"{sample_dir.name}: source ID does not match expected batch source"
            )
        timestamps = {float(frame["timestampSeconds"]) for frame in frames}
        if len(timestamps) != 1:
            raise ValueError(f"{sample_dir.name}: expected one timestamp")
        counts: dict[str, int] = {}
        errors = 0
        for frame in frames:
            for candidate in frame["candidates"]:
                kind = candidate["kind"]
                counts[kind] = counts.get(kind, 0) + 1
                totals[kind] = totals.get(kind, 0) + 1
            for request in frame["requests"]:
                if request.get("error"):
                    name = request["request"]
                    errors += 1
                    request_errors[name] = request_errors.get(name, 0) + 1
        samples.append(
            {
                "timestamp_seconds": next(iter(timestamps)),
                "viewport_results": len(frames),
                "candidate_counts": dict(sorted(counts.items())),
                "request_error_count": errors,
                "runtime_elapsed_seconds": _metric(ELAPSED_PATTERN, metrics, float),
                "maximum_resident_set_size_bytes": _metric(
                    RSS_PATTERN, metrics, int
                ),
            }
        )
    samples.sort(key=lambda item: item["timestamp_seconds"])
    runtimes = [
        sample["runtime_elapsed_seconds"]
        for sample in samples
        if sample["runtime_elapsed_seconds"] is not None
    ]
    rss_values = [
        sample["maximum_resident_set_size_bytes"]
        for sample in samples
        if sample["maximum_resident_set_size_bytes"] is not None
    ]
    return {
        "schema_version": 1,
        "source_id": expected_source_id,
        "sample_count": len(samples),
        "timestamps_seconds": [sample["timestamp_seconds"] for sample in samples],
        "candidate_counts_total": dict(sorted(totals.items())),
        "request_error_counts": dict(sorted(request_errors.items())),
        "runtime_elapsed_seconds_total": sum(runtimes) if runtimes else None,
        "runtime_elapsed_seconds_max": max(runtimes) if runtimes else None,
        "maximum_resident_set_size_bytes_max": max(rss_values) if rss_values else None,
        "samples": samples,
        "limitations": [
            "Fixed timestamps are scene-distributed bootstrap samples, not event ground truth.",
            "Candidate counts are unreviewed and do not establish recall, precision, duplicates, tracking, or editorial value.",
            "Runtime excludes viewport extraction and may include per-sample process startup.",
            "No backend or perception projection strategy is selected by this evidence.",
        ],
    }


def main() -> int:
    if len(sys.argv) < 4:
        raise SystemExit(
            f"usage: {sys.argv[0]} OUTPUT_JSON SOURCE_ID SAMPLE_DIR..."
        )
    output = Path(sys.argv[1])
    if output.exists():
        raise SystemExit("refusing to overwrite batch summary")
    result = summarize([Path(path) for path in sys.argv[3:]], sys.argv[2])
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
