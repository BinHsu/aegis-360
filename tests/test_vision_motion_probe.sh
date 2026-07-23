#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-motion-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for index in 0 1 2 3 4 5 6 7 8 9; do
    x=$((80 + 4 * index))
    y=$((90 + 2 * index))
    ffmpeg -hide_banner -loglevel error -y \
        -f lavfi -i "color=c=gray:s=640x360:d=0.1,drawgrid=w=40:h=40:t=2:c=white@0.8,drawbox=x=$x:y=$y:w=180:h=120:c=red:t=fill,drawbox=x=$((x + 25)):y=$((y + 20)):w=45:h=35:c=black:t=fill" \
        -frames:v 1 "$work_dir/source-$index.png"
done
ffmpeg -hide_banner -loglevel error -y -framerate 10 \
    -i "$work_dir/source-%d.png" -c:v libx264 -pix_fmt yuv420p "$work_dir/synthetic.mp4"

"$repo_dir/scripts/run_vision_motion_probe.sh" \
    "$work_dir/synthetic.mp4" "$work_dir/evidence.json" synthetic-pan 0 1 10

python3 - "$work_dir/evidence.json" "$work_dir" <<'PY'
import json
import math
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
assert result["schemaVersion"] == 1
assert result["sourceId"] == "synthetic-pan"
assert result["provenance"]["backendId"] == "VNTrackHomographicImageRegistrationRequest"
assert result["summary"]["requestedFrameCount"] >= 9
measured = [row for row in result["observations"] if row["state"] == "measured"]
if result["summary"]["outcome"] == "motion_observations_returned":
    assert result["summary"]["measuredPairCount"] >= 7
    assert result["summary"]["rootMeanSquareTranslationPixels"] is not None
    assert result["summary"]["maximumTranslationPixels"] < 30
    assert measured
    assert all(len(row["homographyRowMajor"]) == 9 for row in measured)
    assert all(math.isfinite(row["rotationProxyRadians"]) for row in measured)
else:
    assert result["summary"]["outcome"] == "no_motion_observations"
    assert result["summary"]["measuredPairCount"] == 0
    assert result["summary"]["errorPairCount"] == result["summary"]["requestedFrameCount"] - 1
    assert all(row["state"] == "error" for row in result["observations"])
    assert all("/" not in (row.get("error") or "") for row in result["observations"])
encoded = json.dumps(result)
assert sys.argv[2] not in encoded
assert "/Users/" not in encoded
assert "synthetic.mp4" not in encoded
assert any("No stabilization" in item for item in result["limitations"])
PY

echo "Vision motion probe synthetic test passed"
