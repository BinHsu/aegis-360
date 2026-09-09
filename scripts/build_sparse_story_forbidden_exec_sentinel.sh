#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: build_sparse_story_forbidden_exec_sentinel.sh OUTPUT_RUNTIME_ROOT" >&2
    exit 64
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
source_path="${repo_dir}/tools/sparse_story_forbidden_exec_sentinel.c"
[ -f "$source_path" ] && [ ! -L "$source_path" ] || {
    echo "sentinel source must be a regular non-symlink file" >&2
    exit 70
}
output_root=$1
case "$output_root" in
    /*) ;;
    *) echo "output root must be absolute" >&2; exit 64 ;;
esac
output_parent=$(dirname -- "$output_root")
output_name=$(basename -- "$output_root")
[ "${output_parent}/${output_name}" = "$output_root" ] || {
    echo "output root spelling must be canonical" >&2
    exit 64
}
case "$output_name" in
    ""|.*|*[!A-Za-z0-9._-]*) echo "output root basename is unsafe" >&2; exit 64 ;;
esac
case "$output_name" in
    [A-Za-z0-9]*) ;;
    *) echo "output root basename is unsafe" >&2; exit 64 ;;
esac
[ "${#output_name}" -le 128 ] || {
    echo "output root basename is too long" >&2
    exit 64
}
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] || {
    echo "output parent must be an existing real directory" >&2
    exit 64
}
resolved_parent=$(CDPATH= cd -- "$output_parent" && pwd -P)
[ "$resolved_parent" = "$output_parent" ] || {
    echo "output parent spelling must be canonical" >&2
    exit 64
}
/usr/bin/stat -f '%u %Lp' "$resolved_parent" | {
    read -r owner mode
    [ "$owner" = "$(/usr/bin/id -u)" ] && [ "$mode" = 700 ] || {
        echo "output parent must be caller-owned with mode 0700" >&2
        exit 64
    }
}
candidate_root="${resolved_parent}/${output_name}"
case "${candidate_root}/" in
    "${repo_dir}/"*) echo "output root must be outside the repository" >&2; exit 64 ;;
esac
[ "$candidate_root" = "$output_root" ] || {
    echo "output root spelling must be canonical" >&2
    exit 64
}
[ ! -e "$candidate_root" ] || {
    echo "refusing to overwrite existing output root" >&2
    exit 64
}
created=0
root_identity=
bin_identity=
output_identity=
identity() { /usr/bin/stat -f '%d:%i:%u' "$1" 2>/dev/null || true; }
rollback() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$created" = 1 ]; then
        if [ -n "$root_identity" ] && [ "$(identity "$candidate_root")" = "$root_identity" ]; then
            /bin/chmod 0700 "$candidate_root" 2>/dev/null || true
        fi
        if [ -n "$bin_identity" ] && [ "$(identity "${candidate_root}/bin")" = "$bin_identity" ]; then
            /bin/chmod 0700 "${candidate_root}/bin" 2>/dev/null || true
        fi
        if [ -n "$output_identity" ] && [ "$(identity "${candidate_root}/bin/aegis-forbidden-exec-sentinel")" = "$output_identity" ]; then
            /bin/rm -f -- "${candidate_root}/bin/aegis-forbidden-exec-sentinel"
        fi
        if [ -n "$bin_identity" ] && [ "$(identity "${candidate_root}/bin")" = "$bin_identity" ]; then
            /bin/rmdir "${candidate_root}/bin" 2>/dev/null || true
        fi
        if [ -n "$root_identity" ] && [ "$(identity "$candidate_root")" = "$root_identity" ]; then
            /bin/rmdir "$candidate_root" 2>/dev/null || true
        fi
    fi
    exit "$status"
}
trap rollback EXIT HUP INT TERM
/bin/mkdir -m 0700 "$candidate_root"
created=1
root_identity=$(identity "$candidate_root")
[ -n "$root_identity" ] || { echo "could not retain output root identity" >&2; exit 70; }
/bin/mkdir -m 0700 "${candidate_root}/bin"
bin_identity=$(identity "${candidate_root}/bin")
[ -n "$bin_identity" ] || { echo "could not retain output bin identity" >&2; exit 70; }
output="${candidate_root}/bin/aegis-forbidden-exec-sentinel"
/usr/bin/xcrun --sdk macosx clang -std=c11 -Os -Wall -Wextra -Werror -Wpedantic \
    -fstack-protector-strong -arch arm64 -mmacosx-version-min=15.0 \
    "$source_path" -o "$output"
output_identity=$(identity "$output")
[ -n "$output_identity" ] || { echo "could not retain sentinel identity" >&2; exit 70; }
/usr/bin/codesign --force --sign - --timestamp=none "$output"
output_identity=$(identity "$output")
[ -n "$output_identity" ] || { echo "sentinel identity changed during signing" >&2; exit 70; }
/usr/bin/codesign --verify --strict "$output"
[ "$(/usr/bin/lipo -archs "$output")" = arm64 ] || {
    echo "sentinel is not thin arm64" >&2
    exit 70
}
/bin/chmod 0555 "$output"
output_identity=$(identity "$output")
[ -n "$output_identity" ] || { echo "sentinel identity changed during sealing" >&2; exit 70; }
/bin/chmod 0555 "${candidate_root}/bin"
/bin/chmod 0555 "$candidate_root"
created=0
trap - EXIT HUP INT TERM
printf '%s\n' "$output"
