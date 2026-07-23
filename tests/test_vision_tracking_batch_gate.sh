#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-tracking-batch-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
touch "$work_dir/private-one.mp4" "$work_dir/private-two.mp4"
cat > "$work_dir/fake-gate" <<'SH'
#!/bin/sh
set -eu
mkdir -p "$2"
case "$4" in
 track-a) outcome=tracking_observations_returned; tracked=4; lost=0; step=0.05; seam=1 ;;
 *) outcome=no_tracking_observations; tracked=0; lost=4; step=null; seam=0 ;;
esac
cat > "$2/tracking.json" <<EOF
{"summary":{"outcome":"$outcome","requestedFrameCount":4,"trackedFrameCount":$tracked,"lostFrameCount":$lost,"errorFrameCount":0,"persistenceRatio":$(awk -v n="$tracked" 'BEGIN {print n/4}'),"maximumSphericalCenterStepRadians":$step,"seamCrossingCount":$seam}}
EOF
SH
chmod +x "$work_dir/fake-gate"
cat > "$work_dir/manifest.json" <<EOF
{"schemaVersion":1,"clips":[
{"clipId":"clip-a","inputVideo":"$work_dir/private-one.mp4","sourceId":"source-a","trackId":"track-a","startSeconds":1,"durationSeconds":2,"framesPerSecond":2,"viewportYawDegrees":179,"boxX":0.1,"boxY":0.2,"boxWidth":0.3,"boxHeight":0.4},
{"clipId":"clip-b","inputVideo":"$work_dir/private-two.mp4","sourceId":"source-b","trackId":"track-b","startSeconds":3,"durationSeconds":2,"framesPerSecond":2,"viewportYawDegrees":0,"boxX":0.2,"boxY":0.2,"boxWidth":0.2,"boxHeight":0.3}]}
EOF
AEGIS_TRACKING_GATE_RUNNER="$work_dir/fake-gate" \
 python3 "$repo_dir/scripts/run_vision_tracking_batch_gate.py" \
 "$work_dir/manifest.json" "$work_dir/output" >/dev/null
python3 - "$work_dir/output/batch-report.json" "$work_dir" <<'PY'
import json, sys
report = json.load(open(sys.argv[1], encoding="utf-8"))
aggregate = report["aggregate"]
assert report["clipCount"] == 2
assert aggregate["requestedFrameCount"] == 8
assert aggregate["trackedFrameCount"] == aggregate["lostFrameCount"] == 4
assert aggregate["weightedPersistenceRatio"] == 0.5
assert aggregate["maximumSphericalCenterStepRadians"] == 0.05
assert aggregate["seamCrossingCount"] == 1
assert aggregate["outcomeCounts"] == {"no_tracking_observations": 1, "tracking_observations_returned": 1}
encoded = json.dumps(report)
assert sys.argv[2] not in encoded and "private-" not in encoded
assert "/Users/" not in encoded and "inputVideo" not in encoded
PY
if AEGIS_TRACKING_GATE_RUNNER="$work_dir/fake-gate" \
 python3 "$repo_dir/scripts/run_vision_tracking_batch_gate.py" \
 "$work_dir/manifest.json" "$work_dir/output" >/dev/null 2>&1; then
 echo "existing output directory unexpectedly succeeded" >&2; exit 1
fi
echo "Vision tracking batch gate test passed"
