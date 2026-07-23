#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-fixed-forward.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

fixture="$work_dir/synthetic-erp-av.mkv"
output="$work_dir/fixed-forward.mp4"
"$repo_dir/scripts/generate_synthetic_erp_av.sh" "$fixture"
"$repo_dir/scripts/render_fixed_forward_baseline.sh" \
  "$fixture" "$output" 0.5 1.0 0 0 90 640 360

video_shape=$(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=width,height,nb_read_frames \
  -of csv=p=0:s=x "$output")
[ "$video_shape" = "640x360x10" ] || {
  echo "unexpected output video stream: $video_shape" >&2
  exit 1
}

stream_types=$(ffprobe -v error -show_entries stream=codec_type \
  -of csv=p=0 "$output" | sort | tr '\n' ' ')
[ "$stream_types" = "audio video " ] || {
  echo "expected one audio and one video stream, got: $stream_types" >&2
  exit 1
}

first_last_pts=$(ffprobe -v error -select_streams v:0 -show_packets \
  -show_entries packet=pts_time -of csv=p=0 "$output" \
  | awk 'NR == 1 { first=$1 } { last=$1 } END { print first " " last }')
[ "$first_last_pts" = "0.000000 0.900000" ] || {
  echo "unexpected first/last video PTS: $first_last_pts" >&2
  exit 1
}

durations=$(ffprobe -v error -show_entries stream=codec_type,duration \
  -of csv=p=0 "$output")
video_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "video" { print $2 }')
audio_duration=$(printf '%s\n' "$durations" | awk -F, '$1 == "audio" { print $2 }')
awk -v v="$video_duration" -v a="$audio_duration" 'BEGIN {
  if (v < 0.99 || v > 1.01 || a < 0.99 || a > 1.03 || (v-a > 0.04) || (a-v > 0.04)) exit 1
}' || {
  echo "unexpected A/V duration: video=$video_duration audio=$audio_duration" >&2
  exit 1
}

ffmpeg -v error -i "$output" -f null -

if "$repo_dir/scripts/render_fixed_forward_baseline.sh" \
  "$fixture" "$output" >/dev/null 2>&1; then
  echo "renderer unexpectedly overwrote an existing output" >&2
  exit 1
fi

echo "PASS: fixed-forward baseline produced a decodable 1 s proxy with normalized, synchronized A/V timing"
