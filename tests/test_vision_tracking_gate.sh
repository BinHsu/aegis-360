#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-tracking-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for index in 0 1 2 3 4 5; do
    x=$((80 + index * 30))
    ffmpeg -hide_banner -loglevel error -y \
        -f lavfi -i "color=c=gray:s=640x360:d=0.1,drawbox=x=$x:y=110:w=120:h=100:color=white:t=fill,drawbox=x=$((x + 15)):y=125:w=35:h=35:color=black:t=fill,drawbox=x=$((x + 65)):y=165:w=40:h=30:color=red:t=fill" \
        -frames:v 1 "$work_dir/frame-$index.png"
done

{
    printf '{"sourceId":"synthetic-moving-box","trackId":"box-1","viewportYawDegrees":179,"viewportPitchDegrees":0,"horizontalFovDegrees":100,'
    printf '"initialBox":{"x":0.125,"y":0.416666667,"width":0.1875,"height":0.277777778},"frames":['
    separator=
    for index in 0 1 2 3 4 5; do
        printf '%s{"image":"%s/frame-%s.png","timestampSeconds":%s}' \
            "$separator" "$work_dir" "$index" "$index"
        separator=,
    done
    printf ']}\n'
} > "$work_dir/input.json"

swiftc "$repo_dir/tools/vision_tracking_gate.swift" -o "$work_dir/vision_tracking_gate"
"$work_dir/vision_tracking_gate" "$work_dir/input.json" "$work_dir/output.json"

python3 - "$work_dir/output.json" "$work_dir" <<'PY'
import json
import math
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
assert result["schemaVersion"] == 1
assert result["sourceId"] == "synthetic-moving-box"
assert result["trackId"] == "box-1"
assert result["provenance"]["backendId"] == "VNTrackObjectRequest"
assert result["summary"]["requestedFrameCount"] == 6
tracked = [row for row in result["observations"] if row["state"] == "tracked"]
if result["summary"]["outcome"] == "tracking_observations_returned":
    assert result["summary"]["trackedFrameCount"] >= 5
    assert result["summary"]["persistenceRatio"] >= 5 / 6
    assert all(row["boundingBox"] is not None for row in tracked)
    assert all(-math.pi <= row["yawRadians"] < math.pi for row in tracked)
    assert any(row["sphericalCenterStepRadians"] is not None for row in tracked)
    assert result["summary"]["maximumSphericalCenterStepRadians"] < math.radians(15)
    assert result["summary"]["seamCrossingCount"] >= 1
else:
    assert result["summary"]["outcome"] == "no_tracking_observations"
    assert result["summary"]["trackedFrameCount"] == 0
    assert result["summary"]["lostFrameCount"] + result["summary"]["errorFrameCount"] == 6
    assert all(row["state"] in {"lost", "error"} for row in result["observations"])
    assert all("/" not in (row.get("error") or "") for row in result["observations"])
encoded = json.dumps(result)
assert sys.argv[2] not in encoded
assert "/Users/" not in encoded
assert any("confidence is perception evidence" in item for item in result["limitations"])
PY

mkdir "$work_dir/existing-output"
if "$repo_dir/scripts/run_vision_tracking_gate.sh" \
    "$work_dir/missing.mp4" "$work_dir/existing-output" safe track \
    0 1 2 0 0.1 0.1 0.2 0.2 >/dev/null 2>&1; then
    echo "missing input unexpectedly succeeded" >&2
    exit 1
fi

echo "Vision tracking gate synthetic test passed"
