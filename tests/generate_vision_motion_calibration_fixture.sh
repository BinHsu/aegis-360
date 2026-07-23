#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 OUTPUT_DIR" >&2
    exit 2
fi

output_dir=$1
mkdir -p "$output_dir"

width=640
height=360
dx=18
dy=12
angle_degrees=4

# The deliberately asymmetric, high-contrast base makes the registration
# solution unique. The fixture contains no downloaded or real-world media.
ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x18232d:s=${width}x${height}:d=0.1,drawgrid=w=37:h=29:t=2:c=white@0.55,drawbox=x=71:y=43:w=173:h=91:c=red:t=fill,drawbox=x=103:y=66:w=39:h=27:c=black:t=fill,drawbox=x=381:y=211:w=137:h=83:c=yellow:t=fill,drawbox=x=427:y=238:w=31:h=19:c=blue:t=fill" \
    -frames:v 1 "$output_dir/base.png"

# Frame 1 is frame 0 translated +18 px right and +12 px down in top-left
# image coordinates.
ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=black:s=${width}x${height}:d=0.1" \
    -i "$output_dir/base.png" \
    -filter_complex "[0:v][1:v]overlay=x=${dx}:y=${dy}:shortest=1" \
    -frames:v 1 "$output_dir/translation.png"

# FFmpeg's positive rotate angle is clockwise in displayed image coordinates.
ffmpeg -hide_banner -loglevel error -y -i "$output_dir/base.png" \
    -vf "rotate=${angle_degrees}*PI/180:c=black:ow=iw:oh=ih" \
    -frames:v 1 "$output_dir/rotation.png"

cp "$output_dir/base.png" "$output_dir/0-translation.png"
cp "$output_dir/translation.png" "$output_dir/1-translation.png"
cp "$output_dir/base.png" "$output_dir/0-rotation.png"
cp "$output_dir/rotation.png" "$output_dir/1-rotation.png"

ffmpeg -hide_banner -loglevel error -y -framerate 1 \
    -i "$output_dir/%d-translation.png" -c:v libx264 -crf 0 -pix_fmt yuv444p \
    "$output_dir/translation.mp4"
ffmpeg -hide_banner -loglevel error -y -framerate 1 \
    -i "$output_dir/%d-rotation.png" -c:v libx264 -crf 0 -pix_fmt yuv444p \
    "$output_dir/rotation.mp4"
