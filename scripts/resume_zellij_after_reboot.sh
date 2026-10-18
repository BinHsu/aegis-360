#!/bin/sh
# Reattach this workstation's saved Zellij session after a reboot.
set -eu

repo=/Users/bin.hsu/Documents/aegis-360
session=vitreous-hill

if [ ! -d "$repo/.git" ]; then
    printf '%s\n' "Repository missing: $repo" >&2
    exit 2
fi
if ! command -v zellij >/dev/null 2>&1; then
    printf '%s\n' 'Zellij is not installed or not on PATH.' >&2
    exit 2
fi
if [ -n "${ZELLIJ:-}" ]; then
    printf '%s\n' 'Already inside Zellij; run this from a normal terminal.' >&2
    exit 2
fi

cd "$repo"
printf 'Attaching to saved Zellij session: %s\n' "$session"
printf '%s\n' 'If Zellij reports that it cannot find this session, stop; this script will not create an empty replacement.'
exec zellij attach "$session"
