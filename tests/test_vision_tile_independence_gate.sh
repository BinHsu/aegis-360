#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-tiles.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

width=640
height=360
index=0
for shift in 2 8 14 20; do
    color=$(printf '%s\n' red green blue yellow | sed -n "$((index + 1))p")
    ffmpeg -hide_banner -loglevel error -y \
        -f lavfi -i \
        "testsrc2=s=${width}x${height}:d=0.1,drawbox=x=$((71 + 17 * index)):y=$((43 + 13 * index)):w=173:h=91:c=${color}:t=fill,drawbox=x=$((103 + 17 * index)):y=$((66 + 13 * index)):w=39:h=27:c=black:t=fill" \
        -frames:v 1 "$work_dir/base-$index.png"
    ffmpeg -hide_banner -loglevel error -y \
        -f lavfi -i "color=c=black:s=${width}x${height}:d=0.1" \
        -i "$work_dir/base-$index.png" \
        -filter_complex "[0:v][1:v]overlay=x=${shift}:y=0:shortest=1" \
        -frames:v 1 "$work_dir/moved-$index.png"
    index=$((index + 1))
done

ffmpeg -hide_banner -loglevel error -y \
    -i "$work_dir/base-0.png" -i "$work_dir/base-1.png" \
    -i "$work_dir/base-2.png" -i "$work_dir/base-3.png" \
    -filter_complex \
    "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0" \
    -frames:v 1 "$work_dir/full-0.png"
ffmpeg -hide_banner -loglevel error -y \
    -i "$work_dir/moved-0.png" -i "$work_dir/moved-1.png" \
    -i "$work_dir/moved-2.png" -i "$work_dir/moved-3.png" \
    -filter_complex \
    "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0" \
    -frames:v 1 "$work_dir/full-1.png"

ffmpeg -hide_banner -loglevel error -y -framerate 1 \
    -i "$work_dir/full-%d.png" -c:v ffv1 "$work_dir/full.mkv"

index=0
for position in "0:0" "640:0" "0:360" "640:360"; do
    x=${position%:*}
    y=${position#*:}
    ffmpeg -hide_banner -loglevel error -y -i "$work_dir/full.mkv" \
        -vf "crop=${width}:${height}:${x}:${y}" -c:v ffv1 \
        "$work_dir/tile-$index.mkv"
    "$repo_dir/scripts/run_vision_motion_probe.sh" \
        "$work_dir/tile-$index.mkv" "$work_dir/tile-$index.json" \
        "synthetic-tile-$index" 0 2 1
    index=$((index + 1))
done

python3 - "$work_dir" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
translations = []
for index in range(4):
    result = json.loads((root / f"tile-{index}.json").read_text())
    measured = [
        row for row in result["observations"] if row["state"] == "measured"
    ]
    if measured:
        translations.append(abs(measured[0]["translationXPixels"]))
assert len(translations) == 4, translations
assert translations == sorted(translations), translations
assert translations[-1] - translations[0] >= 8.0, translations
assert all(0.5 <= value <= 24.0 for value in translations), translations
print({"tile_translation_x_pixels": translations})
PY

echo "PASS: independently cropped tiles preserve divergent Vision motion"
