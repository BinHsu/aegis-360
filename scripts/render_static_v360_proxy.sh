#!/bin/sh
set -eu

if [ "$#" -lt 2 ] || [ "$#" -gt 5 ]; then
  echo "usage: $0 INPUT OUTPUT [YAW [PITCH [H_FOV]]]" >&2
  exit 2
fi

input_path=$1
output_path=$2
yaw=${3:-0}
pitch=${4:-0}
h_fov=${5:-90}

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required" >&2
  exit 1
}

ffmpeg -hide_banner -loglevel error -y -i "$input_path" \
  -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=${yaw}:pitch=${pitch}:h_fov=${h_fov}:interp=linear" \
  -an -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -movflags +faststart \
  "$output_path"
