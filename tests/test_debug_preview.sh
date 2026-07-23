#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-debug-preview.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

fixture="$work_dir/source.mkv"
auto="$work_dir/auto.mp4"
debug="$work_dir/debug.mp4"
commands="$work_dir/commands.txt"
trace="$work_dir/trace.tsv"

"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$fixture"
printf '0.5 v360 yaw 45;\n' > "$commands"
"$repo_dir/scripts/render_dynamic_v360_proxy.sh" \
  "$fixture" "$auto" "$commands" 0 2
printf 'start\tend\tyaw\tpitch\tutility\treason\n0\t1\t0\t0\t0.75\tinitial_best\n1\t2\t45\t0\t0.90\tsustained_challenger\n' > "$trace"
python3 "$repo_dir/scripts/render_debug_preview.py" "$auto" "$debug" "$trace"

streams=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$debug" |
  sort | tr '\n' ' ')
[ "$streams" = "audio video " ]

durations=$(ffprobe -v error -show_entries stream=codec_type,duration \
  -of csv=p=0 "$debug")
video_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "video" { print $2 }')
audio_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "audio" { print $2 }')
awk -v v="$video_duration" -v a="$audio_duration" 'BEGIN {
  if (v < 1.99 || v > 2.01 || a < 1.99 || a > 2.02 ||
      v-a > 0.03 || a-v > 0.03) exit 1
}'

auto_hash=$(ffmpeg -v error -ss 0.25 -i "$auto" -frames:v 1 -f framemd5 - |
  awk -F', ' '/^[0-9]/ { print $6 }')
debug_hash=$(ffmpeg -v error -ss 0.25 -i "$debug" -frames:v 1 -f framemd5 - |
  awk -F', ' '/^[0-9]/ { print $6 }')
[ "$auto_hash" != "$debug_hash" ]

ffmpeg -v error -i "$debug" -f null -
if python3 "$repo_dir/scripts/render_debug_preview.py" \
  "$auto" "$debug" "$trace" >"$work_dir/overwrite.log" 2>&1; then
  echo "debug renderer unexpectedly overwrote output" >&2
  exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.log"

echo "PASS: debug decision overlay is decodable, A/V synchronized, and overwrite-safe"
