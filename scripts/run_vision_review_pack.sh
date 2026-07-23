#!/bin/sh
set -eu

if [ "$#" -ne 4 ]; then
    echo "usage: $0 INPUT_VIDEO OUTPUT_DIR SOURCE_ID TIMESTAMPS_FILE" >&2
    exit 2
fi

input_video=$1
output_dir=$2
source_id=$3
timestamps_file=$4
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

[ -f "$input_video" ] || { echo "input video not found" >&2; exit 1; }
[ -f "$timestamps_file" ] || { echo "timestamps file not found" >&2; exit 1; }
case "$source_id" in
    *[!A-Za-z0-9._:-]*|'')
        echo "SOURCE_ID must use only letters, digits, dot, underscore, colon, or hyphen" >&2
        exit 2
        ;;
esac
[ ! -e "$output_dir" ] || {
    echo "refusing to overwrite review-pack output directory" >&2
    exit 1
}

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-review.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
vision_gate=${AEGIS_VISION_GATE_BIN:-"$work_dir/vision_frame_gate"}
if [ -z "${AEGIS_VISION_GATE_BIN:-}" ]; then
    swiftc "$repo_dir/tools/vision_frame_gate.swift" -o "$vision_gate"
fi

mkdir -p "$output_dir"
sample_count=0
while IFS= read -r timestamp || [ -n "$timestamp" ]; do
    case "$timestamp" in ''|'#'*) continue ;; esac
    case "$timestamp" in
        *[!0-9.]*|*.*.*|.*|*.)
            echo "invalid timestamp: $timestamp" >&2
            exit 2
            ;;
    esac
    sample_count=$((sample_count + 1))
    sample_name=$(printf 'sample-%02d-t%s' "$sample_count" "$timestamp")
    sample_dir="$output_dir/$sample_name"
    mkdir -p "$sample_dir"
    input_json="$work_dir/$sample_name.json"
    {
        printf '{"sourceId":"%s","frameIndex":%s,"viewports":[' "$source_id" "$sample_count"
        separator=
        for yaw in 0 90 180 -90; do
            viewport_id="yaw_$yaw"
            [ "$yaw" -ge 0 ] || viewport_id=yaw_minus90
            ffmpeg -hide_banner -loglevel error -y \
                -ss "$timestamp" -i "$input_video" -frames:v 1 \
                -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=$yaw:pitch=0:h_fov=100:interp=linear" \
                "$sample_dir/$viewport_id.png"
            printf '%s{"id":"%s","image":"%s/%s.png","yawDegrees":%s,"pitchDegrees":0,"horizontalFovDegrees":100,"timestampSeconds":%s}' \
                "$separator" "$viewport_id" "$sample_dir" "$viewport_id" "$yaw" "$timestamp"
            separator=,
        done
        printf ']}\n'
    } > "$input_json"
    "$vision_gate" "$input_json" "$sample_dir/vision-frame-gate.json"
done < "$timestamps_file"

[ "$sample_count" -gt 0 ] || {
    echo "timestamps file contains no samples" >&2
    exit 2
}
# Build the renderer argument vector without eval so output paths with spaces remain
# a single argument and no persisted index receives an absolute path.
set -- "$output_dir/review-index.json" "$source_id"
for sample_dir in "$output_dir"/sample-*; do
    timestamp=${sample_dir##*-t}
    set -- "$@" "$sample_dir" "$timestamp"
done
python3 "$repo_dir/scripts/render_vision_review_pack.py" "$@"
printf 'review_index=%s\nsamples=%s\n' "$output_dir/review-index.json" "$sample_count"
