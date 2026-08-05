#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
    echo "usage: $0 INPUT_VIDEO SEED_JSON OUTPUT_DIR" >&2
    exit 2
fi
input_video=$1
seed_json=$2
output_dir=$3
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ -f "$seed_json" ] || { echo "seed JSON not found" >&2; exit 1; }
[ "$(jq -r .schema_version "$seed_json")" = "aegis360.semantic-vision-seed.v1" ] || {
    echo "unsupported seed schema" >&2; exit 2;
}

"$repo_dir/scripts/run_vision_tracking_gate.sh" \
    "$input_video" "$output_dir" \
    "$(jq -r .source_id "$seed_json")" \
    "$(jq -r .track_id "$seed_json")" \
    "$(jq -r .start_seconds "$seed_json")" \
    "$(jq -r .duration_seconds "$seed_json")" \
    "$(jq -r .sample_fps "$seed_json")" \
    "$(jq -r .viewport.yaw_degrees "$seed_json")" \
    "$(jq -r .initial_box_vision_bottom_left_normalized.x "$seed_json")" \
    "$(jq -r .initial_box_vision_bottom_left_normalized.y "$seed_json")" \
    "$(jq -r .initial_box_vision_bottom_left_normalized.width "$seed_json")" \
    "$(jq -r .initial_box_vision_bottom_left_normalized.height "$seed_json")" \
    "$(jq -r .viewport.width_pixels "$seed_json")" \
    "$(jq -r .viewport.height_pixels "$seed_json")" \
    "$(jq -r .viewport.pitch_degrees "$seed_json")" \
    "$(jq -r .viewport.horizontal_fov_degrees "$seed_json")"
