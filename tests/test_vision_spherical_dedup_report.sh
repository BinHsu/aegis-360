#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-dedup-report-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

mkdir -p "$work_dir/input/sample-01-t1" "$work_dir/input/sample-02-t2"
for sample in 1 2; do
    timestamp=$sample
    evidence="$work_dir/input/sample-0${sample}-t${timestamp}/vision-frame-gate.json"
    sed \
        -e "s/TIMESTAMP/$timestamp/g" \
        -e "s/SECOND_YAW/0.02/g" \
        > "$evidence" <<'JSON'
{
  "schemaVersion": 1,
  "provenance": {
    "adapterId": "fixture", "adapterVersion": "1",
    "backendId": "mock", "projectionStrategy": "overlapping-viewports"
  },
  "frames": [
    {
      "sourceId": "privacy-safe-fixture", "frameIndex": 0,
      "timestampSeconds": TIMESTAMP,
      "candidates": [{
        "id": "front:human:0", "kind": "human", "confidence": 0.99,
        "viewportId": "front", "yawRadians": 0.0, "pitchRadians": 0.0,
        "horizontalFovRadians": 0.3,
        "boundingBox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}
      }]
    },
    {
      "sourceId": "privacy-safe-fixture", "frameIndex": 0,
      "timestampSeconds": TIMESTAMP,
      "candidates": [{
        "id": "right:human:0", "kind": "human", "confidence": 0.01,
        "viewportId": "right", "yawRadians": SECOND_YAW, "pitchRadians": 0.0,
        "horizontalFovRadians": 0.3,
        "boundingBox": {"x": 0.5, "y": 0.2, "width": 0.3, "height": 0.4}
      }]
    }
  ]
}
JSON
done

"$repo_dir/scripts/run_vision_spherical_dedup_report.sh" \
    "$work_dir/input" "$work_dir/report.json" "$work_dir/trace.json"

python3 - "$work_dir/report.json" "$work_dir/trace.json" "$work_dir" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
trace = json.load(open(sys.argv[2], encoding="utf-8"))
assert report["raw_candidate_count"] == 4
assert report["cluster_count"] == 2
assert report["raw_kind_counts"] == {"human": 4}
assert report["deduplicated_kind_counts"] == {"human": 2}
assert report["samples"][0]["clusters"][0]["member_ids"] == [
    "front:human:0", "right:human:0"
]
assert report["provenance_summary"]["confidence_used_for_deduplication"] is False
assert trace["scoring_policy"]["detector_confidence_used"] is False
assert {
    component["contribution"]
    for decision in trace["decisions"]
    for candidate in decision["candidates"]
    for component in candidate["score_components"]
} == {0.0}
assert sys.argv[3] not in json.dumps(report)
assert sys.argv[3] not in json.dumps(trace)
assert "bounding_box" not in json.dumps(report)
PY

if "$repo_dir/scripts/run_vision_spherical_dedup_report.sh" \
    "$work_dir/input" "$work_dir/report.json" \
    >"$work_dir/overwrite.stdout" 2>"$work_dir/overwrite.stderr"; then
    echo "runner unexpectedly overwrote output" >&2
    exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.stderr"

if "$repo_dir/scripts/run_vision_spherical_dedup_report.sh" \
    "$work_dir/input" "$work_dir/same.json" "$work_dir/same.json" \
    >"$work_dir/same.stdout" 2>"$work_dir/same.stderr"; then
    echo "runner unexpectedly accepted identical output files" >&2
    exit 1
fi
grep -q "must be different files" "$work_dir/same.stderr"

echo "Vision spherical dedup report mock test passed"
