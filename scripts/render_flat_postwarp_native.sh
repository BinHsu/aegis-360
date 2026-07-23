#!/bin/sh
set -eu

if [ "$#" -lt 3 ]; then
    echo "usage: render_flat_postwarp_native.sh INPUT_VIDEO PLAN.json OUTPUT.mp4 [--start SECONDS] [--duration SECONDS]" >&2
    exit 2
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

xcrun swiftc \
    "$repo_dir/tools/flat_postwarp_renderer.swift" \
    -o "$work_dir/flat_postwarp_renderer"
"$work_dir/flat_postwarp_renderer" "$@"
