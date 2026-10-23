#!/bin/zsh
set -euo pipefail

app=/Volumes/T7/aegis-360-items/toolchains/xcode-27.2-rc/Xcode.app
developer_dir=$app/Contents/Developer

if [[ ! -d /Volumes/T7/aegis-360-items || ! -d $developer_dir ]]; then
  print -u2 'T7 or the approved Xcode 27.2 RC app is missing; nothing was changed.'
  exit 1
fi

version=$(DEVELOPER_DIR=$developer_dir /usr/bin/xcodebuild -version)
if [[ $version != $'Xcode 27.2\nBuild version 27B48' ]]; then
  print -u2 'The Xcode version/build differs from the approved app; nothing was changed.'
  exit 1
fi

if [[ ${1:-} == --check ]]; then
  print 'Approved Xcode 27.2 RC app is present; license interaction was not started.'
  exit 0
fi
if (( $# != 0 )); then
  print -u2 'Usage: accept_t7_xcode_license.sh [--check]'
  exit 2
fi

print 'Apple will display its Xcode license. Read it and decide whether to accept.'
print 'Stop by declining the agreement or pressing Control-C before acceptance.'
print 'You may be asked for your Mac administrator password; do not send it to an agent.'
/usr/bin/sudo /usr/bin/env DEVELOPER_DIR=$developer_dir /usr/bin/xcodebuild -license
