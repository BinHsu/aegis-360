#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=black:s=640x360:d=1,drawbox=x=220:y=80:w=200:h=220:color=white:t=fill" \
    -frames:v 1 "$work_dir/fixture.png"

swiftc "$repo_dir/tools/vision_frame_gate.swift" -o "$work_dir/vision_frame_gate"
printf '{"sourceId":"synthetic-fixture","frameIndex":7,"viewports":[{"id":"front","image":"%s/fixture.png","yawDegrees":0,"pitchDegrees":0,"horizontalFovDegrees":100,"timestampSeconds":1.25}]}\n' \
    "$work_dir" > "$work_dir/input.json"
"$work_dir/vision_frame_gate" "$work_dir/input.json" "$work_dir/output.json"

python3 - "$work_dir/output.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
assert result["schemaVersion"] == 1
assert result["provenance"]["adapterId"] == "apple-vision-frame-gate"
assert result["frames"][0]["sourceId"] == "synthetic-fixture"
assert result["frames"][0]["timestampSeconds"] == 1.25
assert len(result["frames"][0]["requests"]) == 3
assert all("candidateCount" in request for request in result["frames"][0]["requests"])
assert "/Users/" not in json.dumps(result)
PY

printf '{"sourceId":"missing-fixture","frameIndex":8,"viewports":[{"id":"front","image":"%s/missing.png","yawDegrees":0,"pitchDegrees":0,"horizontalFovDegrees":100,"timestampSeconds":2.0}]}\n' \
    "$work_dir" > "$work_dir/missing-input.json"
"$work_dir/vision_frame_gate" "$work_dir/missing-input.json" "$work_dir/missing-output.json"
python3 - "$work_dir/missing-output.json" "$work_dir" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
requests = result["frames"][0]["requests"]
assert all(not request["supported"] for request in requests)
encoded = json.dumps(result)
assert sys.argv[2] not in encoded
assert all(request.get("error") for request in requests)
PY

printf '{"sourceId":"bad\"id","frameIndex":9,"viewports":[{"id":"front","image":"%s/fixture.png","yawDegrees":0,"pitchDegrees":0,"horizontalFovDegrees":100,"timestampSeconds":3.0}]}\n' \
    "$work_dir" > "$work_dir/unsafe-input.json"
if "$work_dir/vision_frame_gate" \
    "$work_dir/unsafe-input.json" "$work_dir/unsafe-output.json" \
    >/dev/null 2> "$work_dir/unsafe-error.txt"; then
    echo "unsafe sourceId unexpectedly succeeded" >&2
    exit 1
fi
[ ! -e "$work_dir/unsafe-output.json" ]

echo "Vision frame gate synthetic test passed"
