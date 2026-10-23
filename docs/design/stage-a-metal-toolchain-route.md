# Stage A Metal compiler route

Status: candidate only; no tool acquired or installed.

The owner-approved offline `MLXVLM` build v2 reached Metal build planning
and failed because the host cannot spawn `metal`. The selected developer
directory is `/Library/Developer/CommandLineTools`; `xcrun --find metal`
fails, no `metal` is present in that toolchain, and no Xcode app was found in
`/Applications`. See
`../experiments/mlx-swift-offline-build-v2-2026-10-23.md`.

Apple's [additional Xcode components documentation](https://developer.apple.com/documentation/Xcode/downloading-and-installing-additional-xcode-components)
says Metal Toolchain is an optional component for building Metal apps and
describes `xcodebuild -downloadComponent metalToolchain`, or export and
import of the component into a selected Xcode. This is an Xcode component
route, not evidence that Command Line Tools alone can host it.

Apple's [release listing](https://developer.apple.com/news/releases/)
identifies stable Xcode 27.1 as build `27A9275` (2026-10-15). Apple's
[system requirements](https://developer.apple.com/xcode/system-requirements/)
list Xcode 27.1 for macOS 26.6 or later, with Swift 6.4 and the macOS 27
SDK. The current macOS 27.0.1 host satisfies that OS floor. These are
official compatibility statements, not a verified local installation.

Apple's [Xcode App Store listing](https://apps.apple.com/us/app/xcode/id497799835)
shows version 27.1 and size 3.1 GB. This listing does not establish the
installed footprint or the size of the optional Metal Toolchain. Apple's
[Command Line Tools documentation](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools)
says `xcodebuild` ships only with Xcode. The documented component commands
therefore offer no supported CLT-only route to add Metal Toolchain on this
host. The smallest documented route appears to be the base Xcode app plus
Metal Toolchain, without optional platform simulators. This is an inference
from Apple's instructions, not a verified local setup.

The repository's storage boundary puts Xcode acquisition, optional Metal
Toolchain and build products on T7. A future candidate would use a pinned
Xcode 27.1 app under `/Volumes/T7/aegis-360-items/toolchains/` and an
operation-local `DEVELOPER_DIR`, avoiding a global `xcode-select` change.
Apple's [Foundation directory documentation](https://developer.apple.com/documentation/foundation/filemanager/searchpathdirectory/developerapplicationdirectory)
says the self-contained Xcode app can be put anywhere. Apple's
[command-line configuration documentation](https://developer.apple.com/cn/documentation/xcode/configuring-command-line-tools-settings)
describes `DEVELOPER_DIR` for per-command Xcode selection. The mounted T7
volume is APFS with about 744 GiB free at the latest check, so it is a
plausible app location. This does not prove first launch and optional
component installation keep every cache off the internal volume; those
writes need inspection before claiming full T7 placement.
The official release listing's download link redirects to Apple ID sign-in
from this environment, so the artifact URL and account route are not yet
available for inspection. Before an installation code can be issued, resolve
the official artifact URL, exact destination and disk footprint, account route,
component artifact and integrity proof, and any writes outside T7. No
download, import, developer-directory change or retry is authorized by the
completed source/build codes.
