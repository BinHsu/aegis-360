# Stage A Metal compiler route

Status: Xcode 27.2 RC app installed on T7; optional Metal Toolchain pending.

On 2026-10-23, the owner supplied the official
`Xcode_27.2_Release_Candidate.xip` download and approved the exact T7
installation plan with code `送 487`. The source was 2,047,348,156 bytes,
SHA-256 `aab47159fa56c8521b0535d5231efc70d330dd4819513c8266a0cf3eceacc425`,
with macOS download-origin metadata pointing to Apple's Developer Tools URL.
`xip --expand` produced one app at
`/Volumes/T7/aegis-360-items/toolchains/xcode-27.2-rc/Xcode.app` (4.0 GiB).
The expanded app reports Xcode 27.2 build `27B48`; operation-local
`DEVELOPER_DIR` makes `xcodebuild -version` report the same. An unsandboxed
`codesign --verify --deep --strict` passed with `valid on disk` and
`satisfies its Designated Requirement`. The same check inside the agent
sandbox returned `CSSMERR_TP_NOT_TRUSTED`, so only the unsandboxed result is
used for this claim. `xip` itself said archive-signature validation was not
attempted. T7 retained about 740 GiB free; the system volume about 34 GiB.
Global `xcode-select` remains on Command Line Tools. The owner accepted the
Xcode license interactively on 2026-10-23. With operation-local
`DEVELOPER_DIR`, `xcrun --find metal` finds the app's stub, but `xcrun metal -v`
reports `cannot execute tool 'metal' due to missing Metal Toolchain` and
directs `xcodebuild -downloadComponent MetalToolchain`. No Metal Toolchain
acquisition or MLX build retry occurred. Apple's documented
`-downloadComponent metalToolchain -exportPath`
can put the exported DMG on T7, but the location and size of MobileAsset's
intermediate cache and the installed component remain unverified. Those
placements must be resolved before changing external or system state.
The read-only `xcodebuild -showComponent metalToolchain` check fails even
outside the agent sandbox because the app expects
`/Library/Developer/PrivateFrameworks/CoreSimulator.framework`, and Xcode
directs `xcodebuild -runFirstLaunch`. The app bundles four Apple packages
totalling about 458 MiB compressed (`CoreTypes`, `MobileDevice`,
`MobileDeviceDevelopment`, `XcodeSystemResources`) whose payloads target
system `/System` and `/Library/Developer` paths. First launch is therefore a
separate system change, not just a link to T7. The owner approved this
one-shot action with `送 226`; `xcodebuild -runFirstLaunch` reported
`Install Succeeded`, and `-checkFirstLaunchStatus` exits zero. Four package
receipts are present, and CoreSimulator.framework now exists under
`/Library/Developer/PrivateFrameworks/`. Global `xcode-select` is unchanged.
Rounded `df` values still show about 34 GiB free internally and 740 GiB on
T7, so an exact byte delta was not measured. `xcrun metal -v` still reports
the optional toolchain missing. An unsandboxed read-only component query
reports build `27B47`, status `uninstalled`; its sandboxed counterpart could
not access MobileAsset. The component's actual download and installed
locations remain unverified on this host.

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

The owner clarified that large Xcode app, Metal component and build data
belong on T7; small local links and configuration needed to use them may
remain on the internal disk. A future candidate would use a pinned
Xcode 27.1 app under `/Volumes/T7/aegis-360-items/toolchains/` and an
operation-local `DEVELOPER_DIR`, avoiding a global `xcode-select` change.
Apple's [Foundation directory documentation](https://developer.apple.com/documentation/foundation/filemanager/searchpathdirectory/developerapplicationdirectory)
says the self-contained Xcode app can be put anywhere. Apple's
[command-line configuration documentation](https://developer.apple.com/cn/documentation/xcode/configuring-command-line-tools-settings)
describes `DEVELOPER_DIR` for per-command Xcode selection. The mounted T7
volume is APFS with about 744 GiB free at the latest check, so it is a
plausible app location. This does not prove first launch and optional
component installation keep all large caches off the internal volume;
those writes need inspection and placement review.
The official release listing's download link redirects to Apple ID sign-in
from this environment, so the artifact URL and account route are not yet
available for inspection. Before an installation code can be issued, resolve
the official artifact URL, exact destination and disk footprint, account route,
component artifact and integrity proof, and any substantial writes outside
T7. No
download, import, developer-directory change or retry is authorized by the
completed source/build codes.
