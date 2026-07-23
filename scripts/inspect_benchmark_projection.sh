#!/bin/sh
set -eu

usage() {
    echo "usage: AEGIS_DATA_DIR=/path/to/data $0 ASSET_ID [OUTPUT_DIR]" >&2
    exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
: "${AEGIS_DATA_DIR:?AEGIS_DATA_DIR must point to the external data root}"

asset_id=$1
input=$AEGIS_DATA_DIR/benchmarks/originals/$asset_id.webm
output_dir=${2:-$AEGIS_DATA_DIR/benchmarks/projection-evidence/$asset_id}

[ -f "$input" ] || {
    echo "benchmark original not found: $asset_id.webm" >&2
    exit 1
}

command -v ffmpeg >/dev/null 2>&1 || {
    echo "ffmpeg is required" >&2
    exit 1
}
command -v ffprobe >/dev/null 2>&1 || {
    echo "ffprobe is required" >&2
    exit 1
}

mkdir -p "$output_dir"

# Deliberately omit filename/path fields so this evidence is safe to share as
# text. The extracted frames remain external data and must not enter Git.
ffprobe -v error \
    -show_entries \
    'format=format_name,duration,size:format_tags:stream=index,codec_name,codec_type,width,height,coded_width,coded_height,sample_aspect_ratio,display_aspect_ratio,avg_frame_rate,start_time:stream_tags:stream_side_data' \
    -of json "$input" >"$output_dir/probe.json"

duration=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$input")
middle=$(awk -v duration="$duration" 'BEGIN { printf "%.3f", duration / 2 }')
end=$(awk -v duration="$duration" 'BEGIN { printf "%.3f", duration - 5 }')

for sample in "start:5" "middle:$middle" "end:$end"; do
    label=${sample%%:*}
    timestamp=${sample#*:}

    ffmpeg -hide_banner -loglevel error -y -ss "$timestamp" -i "$input" \
        -frames:v 1 -vf 'scale=1024:-2' \
        "$output_dir/${label}_erp.jpg"

    # Order: yaw 0, +90, 180 / -90, north pole, south pole. Successful
    # rendering is not itself proof of ERP; a reviewer must inspect geometry,
    # seam continuity, and pole behavior across all three timestamps.
    ffmpeg -hide_banner -loglevel error -y -ss "$timestamp" -i "$input" \
        -frames:v 1 -filter_complex \
        '[0:v]split=6[a][b][c][d][e][f];[a]v360=input=equirect:output=flat:w=320:h=240:yaw=0:pitch=0:h_fov=90[v0];[b]v360=input=equirect:output=flat:w=320:h=240:yaw=90:pitch=0:h_fov=90[v1];[c]v360=input=equirect:output=flat:w=320:h=240:yaw=180:pitch=0:h_fov=90[v2];[d]v360=input=equirect:output=flat:w=320:h=240:yaw=-90:pitch=0:h_fov=90[v3];[e]v360=input=equirect:output=flat:w=320:h=240:yaw=0:pitch=90:h_fov=90[v4];[f]v360=input=equirect:output=flat:w=320:h=240:yaw=0:pitch=-90:h_fov=90[v5];[v0][v1][v2]hstack=inputs=3[top];[v3][v4][v5]hstack=inputs=3[bottom];[top][bottom]vstack=inputs=2[out]' \
        -map '[out]' "$output_dir/${label}_views.jpg"
done

printf 'projection evidence written for %s\n' "$asset_id"
printf 'review probe.json plus *_erp.jpg and *_views.jpg; do not commit them\n'
