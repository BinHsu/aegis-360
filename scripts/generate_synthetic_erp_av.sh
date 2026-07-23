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

# Deterministic 2-second ERP-like geometry fixture plus a continuous synthetic
# tone. This contains no external media and exists only to test filter control
# timing and A/V timestamp preservation.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi \
  -i "color=c=0x203040:s=1024x512:r=10:d=2" \
  -f lavfi -i "sine=frequency=997:sample_rate=48000:duration=2" \
  -vf "drawgrid=w=128:h=64:t=2:c=white@0.55,drawbox=x=480:y=224:w=64:h=64:c=red:t=fill,drawbox=x=224:y=224:w=64:h=64:c=green:t=fill,drawbox=x=736:y=224:w=64:h=64:c=blue:t=fill,drawbox=x=480:y=32:w=64:h=64:c=yellow:t=fill,drawbox=x=480:y=416:w=64:h=64:c=magenta:t=fill" \
  -map 0:v:0 -map 1:a:0 -c:v ffv1 -pix_fmt yuv444p -c:a pcm_s16le \
  "$output_path"
