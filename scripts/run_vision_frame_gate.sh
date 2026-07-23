#!/bin/sh
set -eu

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "usage: $0 INPUT_VIDEO OUTPUT_DIR TIMESTAMP_SECONDS [SOURCE_ID]" >&2
    exit 2
fi

input_video=$1
output_dir=$2
timestamp=$3
source_id=${4:-benchmark-frame}
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

[ -f "$input_video" ] || {
    echo "input video not found" >&2
    exit 1
}
case "$source_id" in
    *[!A-Za-z0-9._:-]*|'')
        echo "SOURCE_ID must use only letters, digits, dot, underscore, colon, or hyphen" >&2
        exit 2
        ;;
esac

mkdir -p "$output_dir"
for artifact in \
    "$output_dir/vision-frame-gate.json" \
    "$output_dir/vision-frame-gate.compile-metrics.txt" \
    "$output_dir/vision-frame-gate.metrics.txt"; do
    [ ! -e "$artifact" ] || {
        echo "refusing to overwrite output artifact" >&2
        exit 1
    }
done
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-gate.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

compile_metrics="$output_dir/vision-frame-gate.compile-metrics.txt"
/usr/bin/time -l swiftc "$repo_dir/tools/vision_frame_gate.swift" \
    -o "$work_dir/vision_frame_gate" 2> "$compile_metrics"

for yaw in 0 90 180 -90; do
    viewport_id=$(printf 'yaw_%s' "$yaw" | tr -d '-')
    if [ "$yaw" -lt 0 ]; then viewport_id="yaw_minus90"; fi
    ffmpeg -hide_banner -loglevel error -y \
        -ss "$timestamp" -i "$input_video" -frames:v 1 \
        -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=$yaw:pitch=0:h_fov=100:interp=linear" \
        "$work_dir/$viewport_id.png"
done

input_json="$work_dir/input.json"
{
    printf '{"sourceId":"%s","frameIndex":0,"viewports":[' "$source_id"
    separator=
    for yaw in 0 90 180 -90; do
        viewport_id=$(printf 'yaw_%s' "$yaw" | tr -d '-')
        if [ "$yaw" -lt 0 ]; then viewport_id="yaw_minus90"; fi
        printf '%s{"id":"%s","image":"%s/%s.png","yawDegrees":%s,"pitchDegrees":0,"horizontalFovDegrees":100,"timestampSeconds":%s}' \
            "$separator" "$viewport_id" "$work_dir" "$viewport_id" "$yaw" "$timestamp"
        separator=,
    done
    printf ']}\n'
} > "$input_json"

metrics_file="$output_dir/vision-frame-gate.metrics.txt"
set +e
/usr/bin/time -l "$work_dir/vision_frame_gate" \
    "$input_json" "$output_dir/vision-frame-gate.json" \
    2> "$metrics_file"
gate_status=$?
set -e
if [ "$gate_status" -ne 0 ]; then
    echo "Vision gate failed (status $gate_status); metrics follow:" >&2
    tail -n 40 "$metrics_file" >&2
    exit "$gate_status"
fi

printf 'evidence=%s\ncompile_metrics=%s\nruntime_metrics=%s\n' \
    "$output_dir/vision-frame-gate.json" "$compile_metrics" "$metrics_file"
