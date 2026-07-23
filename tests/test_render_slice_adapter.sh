#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-render-adapter.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

source="$work_dir/source.mkv"
"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$source" 2

cat > "$work_dir/camera.json" <<'EOF'
{"schema_version":"aegis360.camera-path.v1","coordinate_units":"radians","keyframes":[
{"timestamp":0,"yaw":0,"pitch":0,"h_fov":1.5707963268,"selected_candidate_id":"front"},
{"timestamp":1,"yaw":1.0,"pitch":0,"h_fov":1.2,"selected_candidate_id":"right"}
]}
EOF
cat > "$work_dir/trace.json" <<'EOF'
{"decisions":[
{"timestamp":10,"selected_candidate_id":"front","reason":"initial_best","candidates":[{"candidate_id":"front","yaw_radians":0,"pitch_radians":0,"utility":0.8}]},
{"timestamp":11,"selected_candidate_id":"right","reason":"sustained_challenger","candidates":[{"candidate_id":"right","yaw_radians":1.0,"pitch_radians":0,"utility":0.9}]}
]}
EOF
cat > "$work_dir/request.json" <<EOF
{"schema_version":"aegis360.render-request.v1","source_media":"$source",
"camera_path":"$work_dir/camera.json","trace":"$work_dir/trace.json",
"start_seconds":0,"duration_seconds":2,
"artifacts":{"fixed":"$work_dir/fixed.mp4","auto":"$work_dir/auto.mp4","debug":"$work_dir/debug.mp4"}}
EOF

python3 "$repo_dir/scripts/render_slice_adapter.py" "$work_dir/request.json"
for output in fixed auto debug; do
  ffmpeg -v error -i "$work_dir/$output.mp4" -f null -
  streams=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 \
    "$work_dir/$output.mp4" | sort | tr '\n' ' ')
  [ "$streams" = "audio video " ]
  durations=$(ffprobe -v error -show_entries stream=codec_type,duration \
    -of csv=p=0 "$work_dir/$output.mp4")
  video=$(printf '%s\n' "$durations" | awk -F, '$1=="video"{print $2}')
  audio=$(printf '%s\n' "$durations" | awk -F, '$1=="audio"{print $2}')
  awk -v v="$video" -v a="$audio" 'BEGIN {
    if (v < 1.99 || v > 2.01 || a < 1.99 || a > 2.02 ||
        v-a > 0.03 || a-v > 0.03) exit 1
  }'
done

printf '{"schema_version":"aegis360.render-request.v1"}\n' > "$work_dir/incomplete.json"
if python3 "$repo_dir/scripts/render_slice_adapter.py" "$work_dir/incomplete.json" \
  >"$work_dir/incomplete.log" 2>&1; then
  echo "incomplete request unexpectedly succeeded" >&2
  exit 1
fi
grep -q "incomplete request" "$work_dir/incomplete.log"
echo "PASS: real adapter produced three decodable synchronized synthetic artifacts"
