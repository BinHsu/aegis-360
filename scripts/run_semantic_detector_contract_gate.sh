#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: run_semantic_detector_contract_gate.sh AEGIS_DATA_DIR OUTPUT.json" >&2
  exit 2
fi
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
data_root=$1
output=$2
model_rel="models/apple/yolov3-tiny-fp16/YOLOv3TinyFP16.mlmodel"
model="$data_root/$model_rel"
model_id="apple_yolov3_tiny_fp16_v2"
model_sha="73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-semantic-contract.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

python3 "$repo_dir/scripts/verify_model_manifest.py" \
  "$repo_dir/model-manifests/manifest.toml" "$data_root"

ffmpeg -hide_banner -loglevel error -f lavfi \
  -i "color=c=0x406080:s=416x416:d=0.04:r=25" \
  -frames:v 1 "$work_dir/input.png"

swiftc "$repo_dir/tools/vision_semantic_detector_gate.swift" \
  -o "$work_dir/vision_semantic_detector_gate"
"$work_dir/vision_semantic_detector_gate" \
  "$model" "$work_dir/input.png" "$output" synthetic-contract 0 \
  "$model_id" "$model_sha"

python3 - "$output" <<'PY'
import json
import sys
from pathlib import Path

document = json.loads(Path(sys.argv[1]).read_text())
assert document["schemaVersion"] == 1
assert document["sourceId"] == "synthetic-contract"
assert document["frameIndex"] == 0
assert document["resultType"] == "VNRecognizedObjectObservation"
assert document["provenance"]["modelId"] == "apple_yolov3_tiny_fp16_v2"
assert document["provenance"]["modelSha256"] == (
    "73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda"
)
assert isinstance(document["detections"], list)
serialized = json.dumps(document)
assert "/Volumes/" not in serialized
assert ".png" not in serialized
print("PASS: semantic detector model/Vision contract")
PY
