#!/bin/sh
set -eu

if [ "$#" -ne 6 ]; then
    echo "usage: $0 INPUT_FLAT_VIDEO OUTPUT_JSON SOURCE_ID START DURATION FPS" >&2
    exit 2
fi

input_video=$1
output_json=$2
source_id=$3
start=$4
duration=$5
fps=$6
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

[ -f "$input_video" ] || { echo "input video not found" >&2; exit 1; }
[ ! -e "$output_json" ] || { echo "refusing to overwrite output" >&2; exit 1; }
case "$source_id" in *[!A-Za-z0-9._:-]*|'') echo "SOURCE_ID must be privacy-safe" >&2; exit 2 ;; esac

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-motion.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

swiftc "$repo_dir/tools/vision_motion_probe.swift" -o "$work_dir/vision_motion_probe"
ffmpeg -hide_banner -loglevel error -y -ss "$start" -t "$duration" -i "$input_video" \
    -vf "fps=$fps" "$work_dir/frame-%06d.png"

set -- "$work_dir"/frame-*.png
[ -f "$1" ] || { echo "no frames extracted" >&2; exit 1; }
dimensions=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height -of csv=p=0:s=, "$1")
width=${dimensions%,*}
height=${dimensions#*,}

input_json="$work_dir/input.json"
{
    printf '{"sourceId":"%s","frameWidth":%s,"frameHeight":%s,"frames":[' \
        "$source_id" "$width" "$height"
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

"$work_dir/vision_motion_probe" "$input_json" "$output_json"
printf 'evidence=%s\n' "$output_json"
