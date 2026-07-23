#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-v360-dynamic.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

filter_help=$(ffmpeg -hide_banner -h filter=v360 2>&1)
printf '%s\n' "$filter_help" | grep -q 'yaw.*\.T\.' || {
  echo "installed v360 does not advertise runtime yaw control" >&2
  exit 1
}
printf '%s\n' "$filter_help" | grep -q 'pitch.*\.T\.' || {
  echo "installed v360 does not advertise runtime pitch control" >&2
  exit 1
}
printf '%s\n' "$filter_help" | grep -q 'h_fov.*\.T\.' || {
  echo "installed v360 does not advertise runtime h_fov control" >&2
  exit 1
}

fixture="$work_dir/synthetic-erp-av.mkv"
output="$work_dir/dynamic.mp4"
commands="$work_dir/path.txt"

"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$fixture" 4

# Step changes happen exactly on frames 5, 10 and 15 at 10 fps. This proves
# timestamped commands, not smooth interpolation between sparse keyframes.
printf '0.5 v360 yaw 45;\n1.0 v360 pitch 35;\n1.5 v360 h_fov 55;\n' > "$commands"
"$repo_dir/scripts/render_dynamic_v360_proxy.sh" "$fixture" "$output" "$commands" 1 2

if "$repo_dir/scripts/render_dynamic_v360_proxy.sh" \
  "$fixture" "$output" "$commands" 1 2 >"$work_dir/overwrite.log" 2>&1; then
  echo "renderer unexpectedly overwrote an existing output" >&2
  exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.log"

video_shape=$(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=width,height,nb_read_frames \
  -of csv=p=0:s=x "$output")
[ "$video_shape" = "640x360x20" ] || {
  echo "unexpected output video stream: $video_shape" >&2
  exit 1
}

stream_types=$(ffprobe -v error -show_entries stream=codec_type \
  -of csv=p=0 "$output" | sort | tr '\n' ' ')
[ "$stream_types" = "audio video " ] || {
  echo "expected one audio and one video stream, got: $stream_types" >&2
  exit 1
}

# Frames in each constant-pose segment must match one another because the
# source image is static, while every command boundary must change pixels.
ffmpeg -v error -i "$output" -map 0:v:0 -f framemd5 - \
  | awk -F', ' '/^[0-9]/ { print $6 }' > "$work_dir/hashes.txt"
hash_at() { sed -n "${1}p" "$work_dir/hashes.txt"; }
[ "$(hash_at 1)" = "$(hash_at 5)" ]
[ "$(hash_at 6)" = "$(hash_at 10)" ]
[ "$(hash_at 11)" = "$(hash_at 15)" ]
[ "$(hash_at 16)" = "$(hash_at 20)" ]
[ "$(hash_at 5)" != "$(hash_at 6)" ]
[ "$(hash_at 10)" != "$(hash_at 11)" ]
[ "$(hash_at 15)" != "$(hash_at 16)" ]

first_last_pts=$(ffprobe -v error -select_streams v:0 -show_packets \
  -show_entries packet=pts_time -of csv=p=0 "$output" \
  | awk 'NR == 1 { first=$1 } { last=$1 } END { print first " " last }')
[ "$first_last_pts" = "0.000000 1.900000" ] || {
  echo "unexpected first/last video PTS: $first_last_pts" >&2
  exit 1
}

durations=$(ffprobe -v error -show_entries stream=codec_type,duration \
  -of csv=p=0 "$output")
video_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "video" { print $2 }')
audio_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "audio" { print $2 }')
awk -v v="$video_duration" -v a="$audio_duration" 'BEGIN {
  if (v < 1.99 || v > 2.01 || a < 1.99 || a > 2.02 || (v-a > 0.03) || (a-v > 0.03)) exit 1
}' || {
  echo "unexpected A/V duration: video=$video_duration audio=$audio_duration" >&2
  exit 1
}

ffmpeg -v error -i "$output" -f null -
echo "PASS: slice-relative v360 commands changed exact frame segments, preserved synthetic A/V timing, and refused overwrite"
