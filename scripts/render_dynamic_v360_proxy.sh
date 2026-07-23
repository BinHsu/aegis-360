#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
  echo "usage: $0 INPUT OUTPUT COMMANDS.txt" >&2
  exit 2
fi

input_path=$1
output_path=$2
commands_path=$3

for tool in ffmpeg; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

[ -f "$commands_path" ] || {
  echo "command file not found: $commands_path" >&2
  exit 1
}

# Important: commands target the default filter name `v360`. Targeting only a
# custom instance suffix (for example `camera`) returns ENOSYS on FFmpeg 8.1.1.
ffmpeg -hide_banner -loglevel error -y -i "$input_path" \
  -filter_complex "[0:v:0]sendcmd=f=${commands_path},v360=input=equirect:output=flat:w=640:h=360:yaw=0:pitch=0:h_fov=90:interp=linear[v]" \
  -map "[v]" -map 0:a:0 -c:v libx264 -preset fast -crf 0 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart "$output_path"
