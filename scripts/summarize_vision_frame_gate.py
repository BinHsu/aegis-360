#!/usr/bin/env python3
"""Print a privacy-safe summary of Vision gate evidence and time metrics."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} EVIDENCE_JSON METRICS_TXT")
    evidence = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    metrics = Path(sys.argv[2]).read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    supported: dict[str, bool] = {}
    errors: dict[str, list[str]] = {}
    for frame in evidence["frames"]:
        for candidate in frame["candidates"]:
            counts[candidate["kind"]] = counts.get(candidate["kind"], 0) + 1
        for request in frame["requests"]:
            name = request["request"]
            supported[name] = supported.get(name, True) and request["supported"]
            if request.get("error"):
                errors.setdefault(name, []).append(request["error"])
    rss_match = re.search(r"(\d+)\s+maximum resident set size", metrics)
    elapsed_match = re.search(r"([0-9.]+)\s+real", metrics)
    summary = {
        "schema_version": evidence["schemaVersion"],
        "source_id": evidence["frames"][0]["sourceId"],
        "timestamps_seconds": sorted(
            {frame["timestampSeconds"] for frame in evidence["frames"]}
        ),
        "viewport_results": len(evidence["frames"]),
        "candidate_counts": dict(sorted(counts.items())),
        "request_supported_on_all_viewports": dict(sorted(supported.items())),
        "request_errors": errors,
        "maximum_resident_set_size_bytes": int(rss_match.group(1)) if rss_match else None,
        "runtime_elapsed_seconds": float(elapsed_match.group(1)) if elapsed_match else None,
        "limitations": evidence["limitations"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
