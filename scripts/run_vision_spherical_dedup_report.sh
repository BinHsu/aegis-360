#!/bin/sh
set -eu

if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]; then
    echo "usage: $0 INPUT_BATCH_DIR OUTPUT_REPORT [GREEDY_TRACE]" >&2
    exit 2
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
input_batch_dir=$1
output_report=$2

if [ "$#" -eq 3 ]; then
    exec python3 "$repo_dir/scripts/report_vision_spherical_dedup.py" \
        "$input_batch_dir" "$output_report" --greedy-trace "$3"
fi
exec python3 "$repo_dir/scripts/report_vision_spherical_dedup.py" \
    "$input_batch_dir" "$output_report"
