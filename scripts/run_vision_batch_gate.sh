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
frame_runner=${AEGIS_VISION_FRAME_RUNNER:-"$repo_dir/scripts/run_vision_frame_gate.sh"}

[ -f "$input_video" ] || {
    echo "input video not found" >&2
    exit 1
}
[ -f "$timestamps_file" ] || {
    echo "timestamps file not found" >&2
    exit 1
}
[ -x "$frame_runner" ] || {
    echo "Vision frame runner is not executable" >&2
    exit 1
}
case "$source_id" in
    *[!A-Za-z0-9._:-]*|'')
        echo "SOURCE_ID must use only letters, digits, dot, underscore, colon, or hyphen" >&2
        exit 2
        ;;
esac
[ ! -e "$output_dir" ] || {
    echo "refusing to overwrite batch output directory" >&2
    exit 1
}

mkdir -p "$output_dir"
sample_dirs_file=$(mktemp "${TMPDIR:-/tmp}/aegis-vision-batch.XXXXXX")
trap 'rm -f "$sample_dirs_file"' EXIT HUP INT TERM

sample_count=0
while IFS= read -r timestamp || [ -n "$timestamp" ]; do
    case "$timestamp" in
        ''|'#'*) continue ;;
        *[!0-9.]*)
            echo "invalid timestamp: $timestamp" >&2
            exit 2
            ;;
    esac
    case "$timestamp" in
        *.*.*|.*|*.) echo "invalid timestamp: $timestamp" >&2; exit 2 ;;
    esac
    sample_count=$((sample_count + 1))
    sample_dir=$(printf '%s/sample-%02d-t%s' "$output_dir" "$sample_count" "$timestamp")
    "$frame_runner" "$input_video" "$sample_dir" "$timestamp" "$source_id"
    printf '%s\n' "$sample_dir" >> "$sample_dirs_file"
done < "$timestamps_file"

[ "$sample_count" -gt 0 ] || {
    echo "timestamps file contains no samples" >&2
    exit 2
}

set -- "$output_dir/vision-batch-summary.json" "$source_id"
while IFS= read -r sample_dir; do
    set -- "$@" "$sample_dir"
done < "$sample_dirs_file"
python3 "$repo_dir/scripts/summarize_vision_batch_gate.py" "$@"
printf 'batch_summary=%s\n' "$output_dir/vision-batch-summary.json"
