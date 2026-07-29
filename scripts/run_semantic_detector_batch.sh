#!/bin/sh
set -eu

if [ "$#" -ne 5 ]; then
  echo "usage: run_semantic_detector_batch.sh INPUT_ERP OUTPUT_DIR SOURCE_ID TIMESTAMPS_FILE AEGIS_DATA_DIR" >&2
  exit 2
fi
input=$1
output=$2
source_id=$3
timestamps_file=$4
data_root=$5
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
model="$data_root/models/apple/yolov3-tiny-fp16/YOLOv3TinyFP16.mlmodel"
model_id="apple_yolov3_tiny_fp16_v2"
model_sha="73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda"

[ -f "$input" ] || { echo "input does not exist" >&2; exit 1; }
[ -f "$timestamps_file" ] || { echo "timestamps file does not exist" >&2; exit 1; }
[ ! -e "$output" ] || { echo "refusing to overwrite output" >&2; exit 1; }
mkdir -p "$output"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-semantic-batch.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
python3 "$repo_dir/scripts/verify_model_manifest.py" \
  "$repo_dir/model-manifests/manifest.toml" "$data_root"
swiftc "$repo_dir/tools/vision_semantic_detector_gate.swift" \
  -o "$work_dir/detector"

sample_count=0
while IFS= read -r timestamp <&3 || [ -n "$timestamp" ]; do
  case "$timestamp" in
    ""|\#*) continue ;;
  esac
  sample_count=$((sample_count + 1))
  sample_dir="$output/sample-$(printf '%03d' "$sample_count")"
  mkdir -p "$sample_dir"
  for yaw in 0 90 180 -90; do
    safe_yaw=$(printf '%s' "$yaw" | sed 's/-/m/')
    frame="$work_dir/frame.png"
    ffmpeg -nostdin -hide_banner -loglevel error -y -ss "$timestamp" -i "$input" \
      -frames:v 1 -vf \
      "v360=input=equirect:output=flat:w=416:h=416:yaw=$yaw:pitch=0:h_fov=100:interp=linear" \
      "$frame"
    "$work_dir/detector" "$model" "$frame" \
      "$sample_dir/yaw-${safe_yaw}.json" "$source_id" "$sample_count" \
      "$model_id" "$model_sha"
  done
  printf '%s\n' "$timestamp" > "$sample_dir/timestamp.txt"
done 3< "$timestamps_file"
[ "$sample_count" -gt 0 ] || { echo "timestamps file contains no samples" >&2; exit 1; }
expected_count=$(awk 'NF && $1 !~ /^#/ { count++ } END { print count + 0 }' "$timestamps_file")
[ "$sample_count" -eq "$expected_count" ] || {
  echo "processed $sample_count of $expected_count timestamp samples" >&2
  exit 1
}

python3 - "$output" "$source_id" <<'PY'
import json
from pathlib import Path
import sys

output = Path(sys.argv[1])
samples = []
totals = {}
for sample_dir in sorted(output.glob("sample-*")):
    timestamp = float((sample_dir / "timestamp.txt").read_text())
    counts = {}
    for path in sorted(sample_dir.glob("yaw-*.json")):
        document = json.loads(path.read_text())
        for detection in document["detections"]:
            label = detection["labels"][0]["identifier"]
            counts[label] = counts.get(label, 0) + 1
            totals[label] = totals.get(label, 0) + 1
    samples.append({
        "timestamp_seconds": timestamp,
        "label_counts": dict(sorted(counts.items())),
        "person_count": counts.get("person", 0),
        "bicycle_count": counts.get("bicycle", 0),
    })
summary = {
    "schema_version": "aegis360.semantic-multiview-batch.v1",
    "source_id": sys.argv[2],
    "sample_count": len(samples),
    "viewport_count_per_sample": 4,
    "model_id": "apple_yolov3_tiny_fp16_v2",
    "label_totals": dict(sorted(totals.items())),
    "samples_with_person": sum(row["person_count"] > 0 for row in samples),
    "samples_with_bicycle": sum(row["bicycle_count"] > 0 for row in samples),
    "samples": samples,
    "limitations": [
        "Fixed samples are coverage probes, not recall ground truth.",
        "Unreviewed detections do not establish subject identity or importance.",
    ],
    "privacy": {"contains_pixels": False, "contains_source_path": False},
}
(output / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, sort_keys=True))
PY
