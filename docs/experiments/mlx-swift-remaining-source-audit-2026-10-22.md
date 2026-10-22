# Remaining MLX Swift source audit, 2026-10-22

Owner code `送 229` authorized the exact three-source plan with SHA-256
`e5d0ac715d8b6b221433099a779eaf020f9f27708aa8313523ad4e42d61f6a90`.
Immediately before acquisition, the three T7 targets were absent, the two
`mlx-swift` gitlinks still matched the plan, and the official numerics tag
still resolved to the expected commit. Each source was fetched at its exact
commit with hooks disabled, no submodule recursion, and no LFS smudge. All
three worktrees are clean. No build, dependency resolution, third-party code
execution, or model invocation ran.

| Source and T7 target | Readback | Static finding |
| --- | --- | --- |
| `https://github.com/ml-explore/mlx.git` at `/Volumes/T7/aegis-360-items/sources/mlx-1f8e74e3` | commit `1f8e74e3f12f31365464a6867c6579f0e9b29d85`; tree `05433bcb7241af2b3531e7ee94f1eed07d4bf15c`; 943 tracked files | Root MIT license, SHA-256 `ccfab7ccb2ea306f71531c8ca77bb55507606cd90768b1e32b8b52ab5b48cf01`. No gitlinks. Its standalone CMake graph contains network `FetchContent` paths, including metal-cpp and JSON; CMake was not run. |
| `https://github.com/ml-explore/mlx-c.git` at `/Volumes/T7/aegis-360-items/sources/mlx-c-ebc88f10` | commit `ebc88f10caa1b625e6b581437a8dea6df8a70085`; tree `dba545156b694c1852de988d8b272975d675bacc`; 136 tracked files | Root MIT license, SHA-256 `44326a4ea062241ae6fc26ee2ec90bdc81af7eb7b9d3966181b733fa69d42057`. No gitlinks. Standalone CMake would fetch its own MLX tag by default; CMake was not run. |
| `https://github.com/apple/swift-numerics.git`, tag `1.0.0`, at `/Volumes/T7/aegis-360-items/sources/swift-numerics-1.0.0` | commit `1e5cbc4e2142677d6695036a748344c8edb83e5c`; tree `4088e93fb52d4400a68a76772bf4c0c2362ae62e`; 53 tracked files; `Package.swift` SHA-256 `f123a719c55d4af5ef43dadcac9c390eaea009c0a2a8fe5ab1743fa5c12b1a70` | Apache-2.0 with Runtime Library Exception in `LICENSE.txt`, SHA-256 `770af8291f708538d8ff885a0bbc4e045cd700531741c4f99528d435c14d7f55`. Swift tools 5.0; `Numerics` product has no external package dependencies. No gitlinks. |

The acquired `mlx` and `mlx-c` trees are separate source checkouts. They
have **not** been placed into the two missing gitlink paths under the
`mlx-swift` checkout. The `mlx-swift` SwiftPM `Cmlx` target points directly
at those paths and excludes the upstream CMake files. This suggests an
offline SwiftPM build can use the pinned trees without running standalone
CMake, but that integration and SwiftPM behavior remain untested. The
`swift-syntax` compiler plugin, local SwiftPM resolution, Metal resource
handling, compiler compatibility, cache/scratch placement, and runtime
isolation still need bounded verification before any native Stage A smoke.

Static inspection is limited to provenance, root licenses, package/CMake
declarations and gitlinks. It does not prove complete license coverage of
vendored files, absence of generated network access, compilation, runtime
compatibility, or semantic behavior. Any next execution must specify exact
T7 scratch/cache/output paths and an offline dependency map; the completed
source-only code does not authorize a build.
