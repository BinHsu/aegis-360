#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 OUTPUT.mkv" >&2
  exit 2
fi

output_path=$1

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required" >&2
  exit 1
}

# A deterministic, synthetic 2:1 frame. The colored markers make static yaw
# changes observable without requiring downloaded footage. This is a geometry
# fixture, not evidence that aspect ratio alone identifies an ERP source.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi \
  -i "color=c=0x203040:s=1024x512:r=10:d=2" \
  -vf "drawgrid=w=128:h=64:t=2:c=white@0.55,drawbox=x=480:y=224:w=64:h=64:c=red:t=fill,drawbox=x=224:y=224:w=64:h=64:c=green:t=fill,drawbox=x=736:y=224:w=64:h=64:c=blue:t=fill,drawbox=x=480:y=32:w=64:h=64:c=yellow:t=fill,drawbox=x=480:y=416:w=64:h=64:c=magenta:t=fill" \
  -c:v ffv1 -pix_fmt yuv444p "$output_path"
