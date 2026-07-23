#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-v360-runtime-pose.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required" >&2
  exit 1
}

filter_help=$(ffmpeg -hide_banner -h filter=v360 2>&1)
printf '%s\n' "$filter_help" | grep -q 'yaw.*\.T\.' || {
  echo "installed v360 does not advertise runtime yaw control" >&2
  exit 1
}

fixture="$work_dir/asymmetric-erp.mkv"
static_output="$work_dir/static-yaw-45.mkv"
t0_output="$work_dir/runtime-t0-yaw-45.mkv"
multi_output="$work_dir/runtime-multi-yaw.mkv"
t0_commands="$work_dir/t0.txt"
multi_commands="$work_dir/multi.txt"

"$repo_dir/scripts/generate_synthetic_erp.sh" "$fixture"

# A single runtime update on the first frame is an absolute-pose control case.
printf '0.0 v360 yaw 45;\n' > "$t0_commands"

# This resembles a planner emitting absolute orientations over time. The path
# reaches yaw=45 once, moves elsewhere, then requests the same yaw=45 again.
printf '%s\n' \
  '0.0 v360 yaw 0;' \
  '0.5 v360 yaw 45;' \
  '1.0 v360 yaw -30;' \
  '1.5 v360 yaw 45;' > "$multi_commands"

ffmpeg -hide_banner -loglevel error -y -i "$fixture" \
  -vf "v360=input=equirect:output=flat:w=640:h=360:yaw=45:pitch=0:h_fov=90:interp=linear" \
  -an -c:v ffv1 "$static_output"
ffmpeg -hide_banner -loglevel error -y -i "$fixture" \
  -vf "sendcmd=f=$t0_commands,v360=input=equirect:output=flat:w=640:h=360:yaw=0:pitch=0:h_fov=90:interp=linear" \
  -an -c:v ffv1 "$t0_output"
ffmpeg -hide_banner -loglevel error -y -i "$fixture" \
  -vf "sendcmd=f=$multi_commands,v360=input=equirect:output=flat:w=640:h=360:yaw=0:pitch=0:h_fov=90:interp=linear" \
  -an -c:v ffv1 "$multi_output"

for name in static t0 multi; do
  case "$name" in
    static) input=$static_output ;;
    t0) input=$t0_output ;;
    multi) input=$multi_output ;;
  esac
  ffmpeg -v error -i "$input" -map 0:v:0 -f framemd5 - \
    | awk -F', ' '/^[0-9]/ { print $6 }' > "$work_dir/$name.hashes"
done

cmp -s "$work_dir/static.hashes" "$work_dir/t0.hashes" || {
  echo "single t=0 runtime yaw=45 did not match static yaw=45" >&2
  exit 1
}

hash_at() { sed -n "${2}p" "$work_dir/$1.hashes"; }
static_45=$(hash_at static 1)
first_runtime_45=$(hash_at multi 6)
returned_runtime_45=$(hash_at multi 16)

[ "$first_runtime_45" = "$static_45" ] || {
  echo "first multi-command yaw=45 did not match static yaw=45" >&2
  exit 1
}
[ "$returned_runtime_45" != "$static_45" ] || {
  echo "repeated multi-command yaw=45 unexpectedly matched the static pose; inspect whether installed FFmpeg behavior changed" >&2
  exit 1
}

echo "PASS: t=0 runtime yaw matched static yaw, while a multi-update path returned different pixels for the same requested yaw"
