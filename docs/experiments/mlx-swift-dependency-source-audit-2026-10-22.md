# MLX Swift dependency source audit, 2026-10-22

Scope: the two source-only acquisitions authorized by owner code `送 148`.
The approved plan is the local ignored JSON with SHA-256
`c84d55d0d6ac1d52ff74dc431dc35b8038080acc121d5a11036ceb8199938c2f`.
Both GitHub tag refs matched the pinned commits immediately before acquisition.
Shallow single-tag clones disabled submodule recursion and LFS smudge. Both
checkouts were read back at the expected HEAD and clean worktree. No package
resolution, compilation, plugin, model, or third-party source execution ran.

| Source | Exact checkout evidence | Static finding |
| --- | --- | --- |
| `https://github.com/ml-explore/mlx-swift.git`, tag `0.32.3`, `/Volumes/T7/aegis-360-items/sources/mlx-swift-0.32.3` | commit `19601207e9a0de51e03ee6ec0c3c5f3784275075`; tree `c3e78d3183a868b074be63acb65614d133b12bdd`; 830 tracked files; `Package.swift` SHA-256 `18c425c41077f355f16bfe7dab9681237c42324d7a11719a472de4765d65b5c1` | Root MIT license. Swift tools 6.3 with experimental C generation; macOS 14+; C++20 and Metal sources. The `MLX` target requires `apple/swift-numerics` `from: 1.0.0`. Linux-only CUDA plugin and argument parser and environment-selected DocC plugin are declared. |
| `https://github.com/swiftlang/swift-syntax.git`, tag `602.0.0`, `/Volumes/T7/aegis-360-items/sources/swift-syntax-602.0.0` | commit `4799286537280063c85a32f09884cfbca301b1a1`; tree `4c96b84ec6f59391ca70d18191500c14854d3d91`; 843 tracked files; `Package.swift` SHA-256 `ae64e22745921f1c739cda2396247f3ad614cc6588ce5d28af59153530f888ec` | Apache-2.0 `LICENSE.txt`; Swift tools 5.9. The manifest declares no external package dependencies. Its library layout depends on local build environment. |

The `mlx-swift` checkout contains two deliberately absent Git submodules:
`Source/Cmlx/mlx` from `https://github.com/ml-explore/mlx` at gitlink
`1f8e74e3f12f31365464a6867c6579f0e9b29d85`, and `Source/Cmlx/mlx-c`
from `https://github.com/ml-explore/mlx-c` at gitlink
`ebc88f10caa1b625e6b581437a8dea6df8a70085`. Its `Cmlx` target uses
those paths, so this source tree is incomplete for a build. The separate
`swift-numerics` range must be pinned and audited before SwiftPM resolution.
Vendored `Source/Cmlx/fmt` has a separate MIT-like license and remains part
of any later build review. `swift-syntax` exposes compiler-plugin products;
their execution has not been reviewed.

This inspection covers top-level source provenance, manifests, licenses,
gitlinks, and visible build/plugin declarations. It does not establish full
transitive supply-chain safety, host compatibility, successful compilation,
offline runtime behavior, native adapter integration, or semantic correctness.
The next bounded step is to pin the missing sources and inspect their nested
graph before proposing an acquisition. The first read-only GitHub tag query for `swift-numerics` failed with DNS
resolution in the sandbox. A later read-only query succeeded and verified
tag `1.0.0` at `1e5cbc4e2142677d6695036a748344c8edb83e5c`.
This is a ref observation, not a source or compatibility audit.
