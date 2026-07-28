#!/bin/sh
set -eu

if [ "$#" -ne 5 ]; then
  echo "usage: run_semantic_detector_multiview_smoke.sh INPUT_ERP OUTPUT_DIR SOURCE_ID TIMESTAMP AEGIS_DATA_DIR" >&2
  exit 2
fi
input=$1
output=$2
source_id=$3
timestamp=$4
data_root=$5
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
model="$data_root/models/apple/yolov3-tiny-fp16/YOLOv3TinyFP16.mlmodel"
model_id="apple_yolov3_tiny_fp16_v2"
model_sha="73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda"

[ -f "$input" ] || { echo "input does not exist" >&2; exit 1; }
[ ! -e "$output" ] || { echo "refusing to overwrite output" >&2; exit 1; }
mkdir -p "$output"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-semantic-smoke.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
python3 "$repo_dir/scripts/verify_model_manifest.py" \
  "$repo_dir/model-manifests/manifest.toml" "$data_root"
swiftc "$repo_dir/tools/vision_semantic_detector_gate.swift" \
  -o "$work_dir/detector"

for yaw in 0 90 180 -90; do
  safe_yaw=$(printf '%s' "$yaw" | sed 's/-/m/')
  frame="$work_dir/yaw-${safe_yaw}.png"
  ffmpeg -hide_banner -loglevel error -ss "$timestamp" -i "$input" \
    -frames:v 1 -vf \
    "v360=input=equirect:output=flat:w=416:h=416:yaw=$yaw:pitch=0:h_fov=100:interp=linear" \
    "$frame"
  "$work_dir/detector" "$model" "$frame" \
    "$output/yaw-${safe_yaw}.json" "$source_id" 0 "$model_id" "$model_sha"
done

python3 - "$output" "$source_id" "$timestamp" <<'PY'
import json
from pathlib import Path
import sys

output = Path(sys.argv[1])
rows = []
counts = {}
for path in sorted(output.glob("yaw-*.json")):
    document = json.loads(path.read_text())
    labels = [
        label["identifier"]
        for detection in document["detections"]
        for label in detection["labels"][:1]
    ]
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    rows.append({
        "viewport_id": path.stem,
        "detection_count": len(document["detections"]),
        "top_labels": labels,
    })
summary = {
    "schema_version": "aegis360.semantic-multiview-smoke.v1",
    "source_id": sys.argv[2],
    "timestamp_seconds": float(sys.argv[3]),
    "viewport": {
        "yaw_degrees": [0, 90, 180, -90],
        "pitch_degrees": 0,
        "horizontal_fov_degrees": 100,
        "width": 416,
        "height": 416,
    },
    "model_id": "apple_yolov3_tiny_fp16_v2",
    "label_counts": dict(sorted(counts.items())),
    "person_or_bicycle_count": counts.get("person", 0) + counts.get("bicycle", 0),
    "viewports": rows,
    "limitations": [
        "Unreviewed detections are not recall ground truth.",
        "This smoke does not establish temporal identity or tracking.",
    ],
}
(output / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, sort_keys=True))
PY
