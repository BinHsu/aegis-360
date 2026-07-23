#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 OUTPUT.mkv" >&2
  exit 2
fi

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required" >&2
  exit 1
}

# 720x360 makes one horizontal pixel equal to 0.5 degrees. Marker centers:
# red=(0,0), blue=(+90,0), green=(-90,0), yellow=(0,+60),
# magenta=(0,-60), cyan=(+/-180,0), orange=(+20,0).
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x203040:s=720x360:r=1:d=1" \
  -vf "drawbox=x=350:y=170:w=20:h=20:c=red:t=fill,\
drawbox=x=530:y=170:w=20:h=20:c=blue:t=fill,\
drawbox=x=170:y=170:w=20:h=20:c=green:t=fill,\
drawbox=x=350:y=50:w=20:h=20:c=yellow:t=fill,\
drawbox=x=350:y=290:w=20:h=20:c=magenta:t=fill,\
drawbox=x=0:y=170:w=10:h=20:c=cyan:t=fill,\
drawbox=x=710:y=170:w=10:h=20:c=cyan:t=fill,\
drawbox=x=390:y=170:w=20:h=20:c=0xff8000:t=fill" \
  -frames:v 1 -c:v ffv1 -pix_fmt rgb24 "$1"
