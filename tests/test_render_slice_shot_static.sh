#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-shot-render.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

source="$work_dir/source.mkv"
"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$source" 2

cat > "$work_dir/camera.json" <<'EOF'
{"schema_version":"aegis360.camera-path.v1","coordinate_units":"radians","keyframes":[
{"timestamp":0,"yaw":3.1241393611,"pitch":0,"h_fov":1.5707963268,"selected_candidate_id":"seam"},
{"timestamp":1,"yaw":1.5707963268,"pitch":0,"h_fov":1.5707963268,"selected_candidate_id":"right"},
{"timestamp":2,"yaw":1.5707963268,"pitch":0,"h_fov":1.5707963268,"selected_candidate_id":"right"}]}
EOF
cat > "$work_dir/trace.json" <<'EOF'
{"decisions":[
{"timestamp":10,"selected_candidate_id":"seam","reason":"initial_best","candidates":[{"candidate_id":"seam","yaw_radians":3.1241393611,"pitch_radians":0,"h_fov_radians":1.5707963268,"utility":0.8}]},
{"timestamp":10.5,"selected_candidate_id":"seam","reason":"held","candidates":[{"candidate_id":"seam","yaw_radians":-3.1241393611,"pitch_radians":0,"h_fov_radians":1.5707963268,"utility":0.8}]},
{"timestamp":11,"selected_candidate_id":"right","reason":"sustained_challenger","candidates":[{"candidate_id":"right","yaw_radians":1.5707963268,"pitch_radians":0,"h_fov_radians":1.5707963268,"utility":0.9}]}
]}
EOF
cat > "$work_dir/request.json" <<EOF
{"schema_version":"aegis360.render-request.v1","render_mode":"shot_static_v360",
"source_media":"$source","camera_path":"$work_dir/camera.json","trace":"$work_dir/trace.json",
"start_seconds":0,"duration_seconds":2,
"framing_safety":{"minimum_horizontal_fov_degrees":110,
"candidate_extent_padding_degrees":10,"maximum_zoom_in_change_degrees":15},
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
    if (v < 1.99 || v > 2.01 || a < 1.99 || a > 2.03 ||
        v-a > 0.04 || a-v > 0.04) exit 1
  }'
done

# The first shot's frames must equal a direct static-v360 reference at the
# seam center; a hard cut at one second must then change the frame content.
ffmpeg -hide_banner -loglevel error -i "$source" -t 1 \
  -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=-180:pitch=0:h_fov=110:interp=linear" \
  -an -c:v libx264 -preset fast -crf 0 -pix_fmt yuv420p "$work_dir/reference.mp4"
reference_hash=$(ffmpeg -v error -i "$work_dir/reference.mp4" -frames:v 1 \
  -map 0:v:0 -f hash -hash md5 -)
first=$(ffmpeg -v error -i "$work_dir/auto.mp4" -frames:v 1 \
  -map 0:v:0 -f hash -hash md5 -)
[ "$reference_hash" = "$first" ]
after_cut=$(ffmpeg -v error -ss 1 -i "$work_dir/auto.mp4" -frames:v 1 \
  -map 0:v:0 -f hash -hash md5 -)
[ "$first" != "$after_cut" ]

echo "PASS: shot-static fallback made a real cut, matched a static-pose reference, and preserved decodable synchronized A/V"
