# Stage A Metal compiler route

Status: Xcode 27.2 RC and Metal Toolchain 27B47 installed; Xcode's compiler stub fails.

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
The owner approved one Apple-managed download/export with `送 151`.
`xcodebuild -downloadComponent metalToolchain -exportPath` downloaded build
`27B47` (838,860,800 declared download bytes), wrote an about 881 MiB
MobileAsset under the system `AssetsV2` tree, and exported an about 866 MiB
bundle to T7 under `toolchains/xcode-27.2-rc/metal-export/`. Its DMG is
907,713,236 bytes with SHA-256
`9a7f61869f1ec662b69634db473f81d7b18f947e9cd81601d4b2825f903b6265`;
the system asset DMG hash matches, and `hdiutil verify` passes. The system
volume's rounded free space fell from 34 to 33 GiB; T7 stayed about 740 GiB
free. No import command was run. Surprisingly, `-showComponent` now says
`installed` and names a mounted cryptex toolchain, and direct execution of
the mounted compiler reports Apple metal 32023.922. However, `xcrun metal -v`
still reports `missing Metal Toolchain` even outside the agent sandbox and
after bypassing the xcrun cache. The ordinary Xcode tool path is therefore
not yet verified. Xcode's local `-help` specifies
`-importComponent metalToolchain -importPath <bundlepath>` for the exported
bundle; Apple documentation describes import as the next separate step.

The approved import attempt returned exit 70, `Asset is already installed`.
The mounted compiler compiled a synthetic Metal kernel after an explicit
`-fmodules-cache-path` flag. The one isolated, network-denied v3 SwiftPM
`MLXVLM` build copied the pinned source snapshot to T7 and reached
`steel_attention.metal`, but exited 1 after 12.6 seconds. Its log shows an
absolute invocation of Xcode's `XcodeDefault.xctoolchain/usr/bin/metal`,
which bypassed the PATH wrapper for the mounted compiler. No `.air` output
or model inference resulted. The v3 stage retains its `build.log` and
`status.json` under the T7 project root. A public-facts-only Claude review
suggested version or registration problems, but neither is confirmed.

The exact `steel_attention.metal` compile command from that failure, with
only the executable changed to the mounted compiler and its module cache
made explicit, exited zero and produced an AIR file. A fresh offline v4
stage used SwiftPM `--build-system native` and the mounted compiler on PATH.
Its `MLXVLM` target build exited zero in 87.3 seconds, with the Swift module
present under its T7 scratch products. The native backend is deprecated.
No `.metallib` or `.air` was found in the v4 scratch tree, so this result
does not prove that GPU shader resources are packaged or that model
inference works. The default Swift build backend still has the absolute
Xcode stub problem.

Upstream's pinned `mlx-swift` install notes explicitly say command-line
SwiftPM cannot build Metal shaders and recommend Xcode. A copy-on-write
Xcode overlay on T7 with only its `metal` stub redirected to the mounted
compiler made direct stub execution work, but `xcrun` and `xcodebuild` under
that overlay stalled in `xcodebuild -license status`; the exact probes were
stopped. The original signed Xcode app was not changed. The overlay remains
an isolated diagnostic artifact and must not be treated as a working Xcode.

The v3 Xcode build manifest names exactly ten generated `.metal` sources.
`scripts/build_mlx_metal_library_v5.py` pinned that set and verified the full
3,457-file dependency snapshot hash before compiling all ten with Apple's
mounted compiler and linking a 2 MiB `default.metallib`. Its SHA-256 is
`8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59`.
A local Metal API probe loaded 232 functions from it on Apple M4. This proves
shader compilation and library loading, but not integration into the MLX
resource bundle or model inference. See
`../experiments/mlx-swift-metal-library-v5-2026-10-23.md`.

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
