#!/bin/sh
set -eu

if [ "$#" -ne 12 ]; then
    echo "usage: $0 INPUT_VIDEO OUTPUT_DIR SOURCE_ID TRACK_ID START DURATION FPS VIEWPORT_YAW BOX_X BOX_Y BOX_W BOX_H" >&2
    exit 2
fi

input_video=$1
output_dir=$2
source_id=$3
track_id=$4
start=$5
duration=$6
fps=$7
viewport_yaw=$8
box_x=$9
box_y=${10}
box_w=${11}
box_h=${12}
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

[ -f "$input_video" ] || { echo "input video not found" >&2; exit 1; }
case "$source_id:$track_id" in
    *[!A-Za-z0-9._:-]*|'') echo "SOURCE_ID and TRACK_ID must be privacy-safe" >&2; exit 2 ;;
esac
[ ! -e "$output_dir" ] || { echo "refusing to overwrite output directory" >&2; exit 1; }
mkdir -p "$output_dir"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-tracking.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

/usr/bin/time -l swiftc "$repo_dir/tools/vision_tracking_gate.swift" \
    -o "$work_dir/vision_tracking_gate" \
    2> "$output_dir/compile-metrics.txt"

ffmpeg -hide_banner -loglevel error -y \
    -ss "$start" -t "$duration" -i "$input_video" \
    -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=$viewport_yaw:pitch=0:h_fov=100:interp=linear,fps=$fps" \
    "$work_dir/frame-%04d.png"

set -- "$work_dir"/frame-*.png
[ -f "$1" ] || { echo "no frames extracted" >&2; exit 1; }
input_json="$work_dir/input.json"
{
    printf '{"sourceId":"%s","trackId":"%s","viewportYawDegrees":%s,"viewportPitchDegrees":0,"horizontalFovDegrees":100,' \
        "$source_id" "$track_id" "$viewport_yaw"
    printf '"initialBox":{"x":%s,"y":%s,"width":%s,"height":%s},"frames":[' \
        "$box_x" "$box_y" "$box_w" "$box_h"
    separator=
    frame_index=0
    for frame_path in "$@"; do
        timestamp=$(awk -v start="$start" -v frame_no="$frame_index" -v fps="$fps" \
            'BEGIN { printf "%.9f", start + frame_no / fps }')
        printf '%s{"image":"%s","timestampSeconds":%s}' "$separator" "$frame_path" "$timestamp"
        separator=,
        frame_index=$((frame_index + 1))
    done
    printf ']}\n'
} > "$input_json"

/usr/bin/time -l "$work_dir/vision_tracking_gate" \
    "$input_json" "$output_dir/tracking.json" \
    2> "$output_dir/runtime-metrics.txt"

python3 - "$output_dir/tracking.json" > "$output_dir/summary.txt" <<'PY'
import json
import math
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
summary = result["summary"]
print(f'requested_frames={summary["requestedFrameCount"]}')
print(f'tracked_frames={summary["trackedFrameCount"]}')
print(f'lost_frames={summary["lostFrameCount"]}')
print(f'error_frames={summary["errorFrameCount"]}')
print(f'persistence_ratio={summary["persistenceRatio"]:.6f}')
step = summary["maximumSphericalCenterStepRadians"]
print("maximum_spherical_center_step_degrees="
      + ("not_observed" if step is None else f"{math.degrees(step):.6f}"))
print(f'seam_crossings={summary["seamCrossingCount"]}')
PY

printf 'evidence=%s\nsummary=%s\n' \
    "$output_dir/tracking.json" "$output_dir/summary.txt"
