#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-spherical-stabilization.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for tool in ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

fixture_dir="$work_dir/fixture"
source="$work_dir/source.mkv"
raw_output="$work_dir/raw.mp4"
stabilized_output="$work_dir/action-natural.mp4"

python3 "$repo_dir/scripts/generate_spherical_stabilization_fixture.py" \
  "$fixture_dir"
"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$source" 6
"$repo_dir/scripts/render_dynamic_v360_proxy.sh" \
  "$source" "$raw_output" "$fixture_dir/raw-v360.commands" 0 6
"$repo_dir/scripts/render_dynamic_v360_proxy.sh" \
  "$source" "$stabilized_output" \
  "$fixture_dir/action-natural-v360.commands" 0 6

python3 - "$fixture_dir/known-motion.csv" "$fixture_dir/manifest.json" <<'PY'
import csv
import json
import math
import sys

with open(sys.argv[1], newline="", encoding="utf-8") as source:
    rows = [{key: float(value) for key, value in row.items()}
            for row in csv.DictReader(source)]
with open(sys.argv[2], encoding="utf-8") as source:
    manifest = json.load(source)

def rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values))

raw_residual = [
    row["raw_yaw_degrees"] - row["intentional_yaw_degrees"] for row in rows
]
stable_residual = [
    row["stabilized_yaw_degrees"] - row["intentional_yaw_degrees"]
    for row in rows
]
rejection_ratio = rms(stable_residual) / rms(raw_residual)
assert rejection_ratio <= 0.15, rejection_ratio

# The stabilized path must retain the complete known slow turn, not converge
# toward a fixed-forward view.  Removing the known residual recovers it at
# every sample rather than only at the endpoints.
recovered_turn = [
    row["stabilized_yaw_degrees"] - residual
    for row, residual in zip(rows, stable_residual)
]
expected_turn = [row["intentional_yaw_degrees"] for row in rows]
assert max(abs(a - b) for a, b in zip(recovered_turn, expected_turn)) < 1e-9
assert recovered_turn[-1] >= 29.0
assert manifest["fixture_kind"] == "oracle_known_motion"
print(f"high_frequency_rejection_ratio={rejection_ratio:.6f}")
print(f"retained_intentional_turn_degrees={recovered_turn[-1]:.6f}")
PY

for output in "$raw_output" "$stabilized_output"; do
  shape=$(ffprobe -v error -count_frames -select_streams v:0 \
    -show_entries stream=width,height,nb_read_frames \
    -of csv=p=0:s=x "$output")
  [ "$shape" = "640x360x60" ] || {
    echo "unexpected rendered stream: $shape" >&2
    exit 1
  }
  ffmpeg -v error -i "$output" -f null -
done

raw_hashes=$(ffmpeg -v error -i "$raw_output" -map 0:v:0 -f framemd5 - \
  | awk -F', ' '/^[0-9]/ { print $6 }')
stable_hashes=$(ffmpeg -v error -i "$stabilized_output" -map 0:v:0 -f framemd5 - \
  | awk -F', ' '/^[0-9]/ { print $6 }')
[ "$raw_hashes" != "$stable_hashes" ] || {
  echo "raw and stabilized projections unexpectedly match" >&2
  exit 1
}

echo "PASS: known spherical shake was reduced while the slow intentional turn was retained"
