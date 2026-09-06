#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: build_sparse_story_native_launcher.sh OUTPUT_RUNTIME_ROOT" >&2
    exit 64
fi
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
source_path=$repo_dir/tools/sparse_story_native_launcher.c
[ -f "$source_path" ] && [ ! -L "$source_path" ] || {
    echo "launcher source must be a regular non-symlink file" >&2
    exit 70
}
output_root=$1
case "$output_root" in
    /*) ;;
    *) echo "output root must be absolute" >&2; exit 64 ;;
esac
case "$output_root/" in
    "$repo_dir/"*) echo "output root must be outside the repository" >&2; exit 64 ;;
esac
if [ ! -e "$output_root" ]; then
    /bin/mkdir -m 0700 "$output_root"
fi
[ -d "$output_root" ] && [ ! -L "$output_root" ] || {
    echo "output root must be a real directory" >&2
    exit 64
}
resolved_root=$(CDPATH= cd -- "$output_root" && pwd -P)
case "$resolved_root/" in
    "$repo_dir/"*) echo "resolved output root must be outside the repository" >&2; exit 64 ;;
esac
/usr/bin/stat -f '%u %Lp' "$resolved_root" | {
    read -r owner mode
    [ "$owner" = "$(/usr/bin/id -u)" ] && [ "$mode" = 700 ] || {
        echo "output root must be caller-owned with mode 0700" >&2
        exit 64
    }
}
/bin/mkdir -m 0700 "$resolved_root/bin"
output=$resolved_root/bin/aegis-sparse-story-launcher
/usr/bin/xcrun --sdk macosx clang -std=c11 -Os -Wall -Wextra -Werror -Wpedantic \
    -fstack-protector-strong -arch arm64 \
    -mmacosx-version-min=15.0 "$source_path" \
    -o "$output"
/usr/bin/codesign --force --sign - --timestamp=none "$output"
/usr/bin/codesign --verify --strict "$output"
[ "$(/usr/bin/lipo -archs "$output")" = arm64 ] || {
    echo "launcher is not thin arm64" >&2
    exit 70
}
/bin/chmod 0555 "$output"
/bin/chmod 0555 "$resolved_root/bin"
/bin/chmod 0555 "$resolved_root"
printf '%s\n' "$output"
