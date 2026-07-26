#!/bin/sh
set -eu

if [ "$#" -ne 6 ]; then
  echo "usage: $0 INPUT OUTPUT COMMANDS START DURATION HFOV" >&2
  exit 2
fi

input_path=$1
output_path=$2
commands_path=$3
start=$4
duration=$5
hfov=$6

[ -f "$input_path" ] || { echo "input not found" >&2; exit 1; }
[ -f "$commands_path" ] || { echo "commands not found" >&2; exit 1; }
[ ! -e "$output_path" ] || {
  echo "refusing to overwrite output: $output_path" >&2
  exit 1
}

ffmpeg -hide_banner -loglevel error -ss "$start" -i "$input_path" \
  -t "$duration" \
  -filter_complex \
  "[0:v:0]setpts=PTS-STARTPTS,sendcmd=f=${commands_path},v360=input=equirect:output=flat:w=1920:h=1080:yaw=0:pitch=0:roll=0:h_fov=${hfov}:interp=linear[v];[0:a:0]asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" -c:v h264_videotoolbox -b:v 16M \
  -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$output_path"
