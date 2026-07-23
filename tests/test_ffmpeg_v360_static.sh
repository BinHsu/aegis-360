#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-v360.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

ffmpeg -hide_banner -h filter=v360 2>&1 | grep -q 'Convert 360 projection' || {
  echo "installed ffmpeg does not provide the v360 filter" >&2
  exit 1
}

fixture="$work_dir/synthetic-erp.mkv"
yaw_zero="$work_dir/yaw-0.mp4"
yaw_ninety="$work_dir/yaw-90.mp4"

"$repo_dir/scripts/generate_synthetic_erp.sh" "$fixture"
"$repo_dir/scripts/render_static_v360_proxy.sh" "$fixture" "$yaw_zero" 0 0 90
"$repo_dir/scripts/render_static_v360_proxy.sh" "$fixture" "$yaw_ninety" 90 0 90

fixture_shape=$(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=width,height,nb_read_frames \
  -of csv=p=0:s=x "$fixture")
[ "$fixture_shape" = "1024x512x20" ] || {
  echo "unexpected fixture stream: $fixture_shape" >&2
  exit 1
}

for proxy in "$yaw_zero" "$yaw_ninety"; do
  proxy_shape=$(ffprobe -v error -count_frames -select_streams v:0 \
    -show_entries stream=width,height,nb_read_frames \
    -of csv=p=0:s=x "$proxy")
  [ "$proxy_shape" = "640x360x20" ] || {
    echo "unexpected proxy stream: $proxy_shape" >&2
    exit 1
  }
  ffmpeg -v error -i "$proxy" -f null -
done

zero_hash=$(ffmpeg -v error -i "$yaw_zero" -map 0:v:0 -f framemd5 - | tail -n 1)
ninety_hash=$(ffmpeg -v error -i "$yaw_ninety" -map 0:v:0 -f framemd5 - | tail -n 1)
[ "$zero_hash" != "$ninety_hash" ] || {
  echo "yaw=0 and yaw=90 unexpectedly decoded to identical frames" >&2
  exit 1
}

echo "PASS: synthetic ERP rendered to distinct, decodable static v360 proxies"
