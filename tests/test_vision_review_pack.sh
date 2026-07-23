#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-review-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

"$repo_dir/scripts/generate_synthetic_erp.sh" "$work_dir/input.mkv"
printf '0\n1\n' > "$work_dir/timestamps.txt"
mock_gate="$work_dir/mock-gate.py"
sed 's/^+//' > "$mock_gate" <<'PY'
#!/usr/bin/env python3
import json, sys
source = json.load(open(sys.argv[1]))
frames = []
for viewport in source["viewports"]:
    frames.append({
        "sourceId": source["sourceId"],
        "frameIndex": source["frameIndex"],
        "timestampSeconds": viewport["timestampSeconds"],
        "viewportCount": 1,
        "requests": [],
        "candidates": [{
            "id": viewport["id"] + ":attention_saliency:0",
            "kind": "attention_saliency",
            "confidence": 0.8,
            "viewportId": viewport["id"],
            "boundingBox": {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5}
        }]
    })
json.dump({"schemaVersion": 1, "frames": frames}, open(sys.argv[2], "w"))
PY
chmod +x "$mock_gate"

AEGIS_VISION_GATE_BIN="$mock_gate" \
    "$repo_dir/scripts/run_vision_review_pack.sh" \
    "$work_dir/input.mkv" "$work_dir/output" synthetic-review \
    "$work_dir/timestamps.txt"

python3 - "$work_dir/output/review-index.json" "$work_dir" <<'PY'
import json, pathlib, sys
index_path = pathlib.Path(sys.argv[1])
result = json.loads(index_path.read_text())
assert result["source_id"] == "synthetic-review"
assert result["candidate_count"] == 8
assert len(result["samples"]) == 2
assert all(sample["human_review"]["reviewed"] is False for sample in result["samples"])
assert all(sample["human_review"]["candidate_recall"] is None for sample in result["samples"])
assert sys.argv[2] not in index_path.read_text()
for sample in result["samples"]:
    assert (index_path.parent / sample["contact_sheet"]).is_file()
    assert len(sample["viewport_images"]) == 4
    assert all((index_path.parent / path).is_file() for path in sample["viewport_images"])
PY

if AEGIS_VISION_GATE_BIN="$mock_gate" \
    "$repo_dir/scripts/run_vision_review_pack.sh" \
    "$work_dir/input.mkv" "$work_dir/output" synthetic-review \
    "$work_dir/timestamps.txt" >"$work_dir/stdout" 2>"$work_dir/stderr"; then
    echo "review runner unexpectedly overwrote output" >&2
    exit 1
fi
grep -q "refusing to overwrite" "$work_dir/stderr"
echo "Vision review pack synthetic test passed"
