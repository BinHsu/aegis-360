#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "testsrc2=size=320x180:rate=30:duration=2" \
    -f lavfi -i "sine=frequency=880:sample_rate=48000:duration=2" \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$work_dir/input.mp4"

python3 - "$work_dir/plan.json" <<'PY'
import json
import sys

frames = []
for index in range(60):
    # Similarity corrections remain bounded inside the 12 px crop.
    tx = (index % 3 - 1) * 4
    frames.append({
        "timestampSeconds": index / 30,
        "correctionHomographyRowMajor": [1, 0, tx, 0, 1, 0, 0, 0, 1],
    })
json.dump({
    "schemaVersion": 1,
    "frameWidth": 320,
    "frameHeight": 180,
    "frames": frames,
    "overscan": {
        "recommendedCenteredCrop": {
            "x": 12, "y": 12, "width": 296, "height": 156,
        }
    },
}, open(sys.argv[1], "w"))
PY

"$repo_dir/scripts/render_flat_postwarp_native.sh" \
    "$work_dir/input.mp4" "$work_dir/plan.json" "$work_dir/output.mp4" \
    --start 0.25 --duration 1.25

ffmpeg -v error -i "$work_dir/output.mp4" -f null -
streams=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$work_dir/output.mp4")
printf '%s\n' "$streams" | grep -qx video
printf '%s\n' "$streams" | grep -qx audio

duration=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$work_dir/output.mp4")
python3 - "$duration" <<'PY'
import sys
duration = float(sys.argv[1])
assert 1.15 <= duration <= 1.40, duration
PY

av_starts=$(ffprobe -v error -show_entries stream=codec_type,start_time \
    -of csv=p=0 "$work_dir/output.mp4")
python3 - "$av_starts" <<'PY'
import sys
rows = [row.split(",") for row in sys.argv[1].splitlines()]
starts = {kind: float(start) for kind, start in rows}
assert abs(starts["video"] - starts["audio"]) <= 1 / 30 + 0.005, starts
PY

# Decode four edge strips. A blank warp border would make one strip nearly black.
for crop in "320:4:0:0" "320:4:0:176" "4:180:0:0" "4:180:316:0"; do
    mean=$(ffmpeg -v error -i "$work_dir/output.mp4" \
        -vf "crop=$crop,format=gray" -frames:v 15 -f rawvideo - |
        od -An -tu1 |
        awk '{for(i=1;i<=NF;i++){sum+=$i;n++}} END{if(n) print sum/n; else print 0}')
    python3 - "$mean" <<'PY'
import sys
assert float(sys.argv[1]) > 8, sys.argv[1]
PY
done

if "$repo_dir/scripts/render_flat_postwarp_native.sh" \
    "$work_dir/input.mp4" "$work_dir/plan.json" "$work_dir/output.mp4" \
    >"$work_dir/overwrite.stdout" 2>"$work_dir/overwrite.stderr"; then
    echo "renderer unexpectedly overwrote existing output" >&2
    exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.stderr"

echo "flat post-warp native synthetic gate passed"
