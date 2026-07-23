#!/bin/sh
set -eu

if [ "$#" -lt 2 ] || [ "$#" -gt 9 ]; then
  echo "usage: $0 INPUT OUTPUT [START [DURATION [YAW [PITCH [H_FOV [WIDTH [HEIGHT]]]]]]]" >&2
  exit 2
fi

input_path=$1
output_path=$2
start=${3:-0}
duration=${4:-10}
yaw=${5:-0}
pitch=${6:-0}
h_fov=${7:-90}
width=${8:-640}
height=${9:-360}

for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool is required" >&2
    exit 1
  }
done

[ -f "$input_path" ] || {
  echo "input not found: $input_path" >&2
  exit 1
}
[ "$input_path" != "$output_path" ] || {
  echo "input and output must differ" >&2
  exit 1
}
[ -d "$(dirname -- "$output_path")" ] || {
  echo "output directory does not exist: $(dirname -- "$output_path")" >&2
  exit 1
}
[ ! -e "$output_path" ] || {
  echo "refusing to overwrite output: $output_path" >&2
  exit 1
}

# This baseline deliberately applies one pose for the entire clip. PTS are
# normalized to the selected segment while original cadence and A/V offset are
# retained. Audio is transcoded because the benchmark WebM codecs are not
# generally valid in the MP4 output container.
ffmpeg -hide_banner -loglevel error \
  -ss "$start" -t "$duration" -i "$input_path" \
  -filter_complex "[0:v:0]v360=input=equirect:output=flat:w=${width}:h=${height}:yaw=${yaw}:pitch=${pitch}:h_fov=${h_fov}:interp=linear,setpts=PTS-STARTPTS[v];[0:a:0]asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart \
  "$output_path"
