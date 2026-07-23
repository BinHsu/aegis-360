#!/bin/sh
set -eu

if [ "$#" -ne 5 ]; then
  echo "usage: $0 INPUT OUTPUT COMMANDS.txt START DURATION" >&2
  exit 2
fi

input_path=$1
output_path=$2
commands_path=$3
start=$4
duration=$5

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

[ ! -e "$output_path" ] || {
  echo "refusing to overwrite existing output: $output_path" >&2
  exit 1
}

awk -v start="$start" -v duration="$duration" 'BEGIN {
  if (start !~ /^[0-9]+([.][0-9]+)?$/ || duration !~ /^[0-9]+([.][0-9]+)?$/ ||
      duration + 0 <= 0) exit 1
}' || {
  echo "START must be nonnegative and DURATION must be positive" >&2
  exit 2
}

# Important: commands target the default filter name `v360`. Targeting only a
# custom instance suffix (for example `camera`) returns ENOSYS on FFmpeg 8.1.1.
#
# Both streams are rebased to zero.  The sendcmd timestamps are consequently
# relative to the requested slice, independent of the source's absolute PTS.
ffmpeg -hide_banner -loglevel error -ss "$start" -i "$input_path" -t "$duration" \
  -filter_complex "[0:v:0]setpts=PTS-STARTPTS,sendcmd=f=${commands_path},v360=input=equirect:output=flat:w=640:h=360:yaw=0:pitch=0:h_fov=90:interp=linear[v];[0:a:0]asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 0 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart "$output_path"
