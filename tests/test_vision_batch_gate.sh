#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-batch-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

: > "$work_dir/fixture.webm"
printf '# dispersed fixture timestamps\n5\n25.5\n90\n' > "$work_dir/timestamps.txt"

mock_runner="$work_dir/mock-frame-runner.sh"
sed 's/^+//' > "$mock_runner" <<'SH'
+#!/bin/sh
+set -eu
+input=$1
+output=$2
+timestamp=$3
+source_id=$4
+[ -f "$input" ]
+mkdir -p "$output"
+printf '{"schemaVersion":1,"frames":[{"sourceId":"%s","timestampSeconds":%s,"candidates":[{"kind":"attention_saliency"}],"requests":[{"request":"attention_saliency","supported":true,"candidateCount":1}]}]}\n' \
+    "$source_id" "$timestamp" > "$output/vision-frame-gate.json"
+printf '0.12 real\n42000000 maximum resident set size\n' > "$output/vision-frame-gate.metrics.txt"
+printf 'compile fixture\n' > "$output/vision-frame-gate.compile-metrics.txt"
SH
chmod +x "$mock_runner"

AEGIS_VISION_FRAME_RUNNER="$mock_runner" \
    "$repo_dir/scripts/run_vision_batch_gate.sh" \
    "$work_dir/fixture.webm" "$work_dir/output" \
    "synthetic-batch" "$work_dir/timestamps.txt"

python3 - "$work_dir/output/vision-batch-summary.json" "$work_dir" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
assert result["schema_version"] == 1
assert result["source_id"] == "synthetic-batch"
assert result["sample_count"] == 3
assert result["timestamps_seconds"] == [5.0, 25.5, 90.0]
assert result["candidate_counts_total"] == {"attention_saliency": 3}
assert result["runtime_elapsed_seconds_total"] == 0.36
assert result["maximum_resident_set_size_bytes_max"] == 42000000
assert sys.argv[2] not in json.dumps(result)
PY

if AEGIS_VISION_FRAME_RUNNER="$mock_runner" \
    "$repo_dir/scripts/run_vision_batch_gate.sh" \
    "$work_dir/fixture.webm" "$work_dir/output" \
    "synthetic-batch" "$work_dir/timestamps.txt" \
    >"$work_dir/overwrite.stdout" 2>"$work_dir/overwrite.stderr"; then
    echo "batch runner unexpectedly overwrote output" >&2
    exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.stderr"

echo "Vision batch gate mock test passed"
