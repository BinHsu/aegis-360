# Isolated MLX Swift Metal library build

Date: 2026-10-23. Host: Apple M4 MacBook Air, macOS 27.0.1, 16 GB unified
memory. All source, tools and products were on the approved T7 project root.
No network, model inference or customer media was used.

The pinned `mlx-swift-lm` 3.32.3 dependency snapshot had 3,457 files and
tree digest `d0075df90a50b5116a008564790f145bc3e4806ea3f1d65eaff277c1a9070aab`.
The v3 Xcode build manifest listed exactly ten generated Metal source files,
matching the source inventory. `scripts/build_mlx_metal_library_v5.py` used
Apple's mounted Metal compiler 32023.922 and Xcode 27.2 RC SDK, with an
explicit T7 module cache and network-denied process wrapper.

All ten `.metal` sources compiled to AIR, and `metallib` linked a 2.0 MiB
`default.metallib` in 4.328 seconds. Its SHA-256 is
`8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59`.
The file identifies as `MetalLib executable (MacOS), version 1.2.7`.
`tools/check_mlx_metallib.swift`, compiled with the pinned Xcode SDK and
macOS 14 deployment target, loaded the library through `MTLDevice.makeLibrary`
and enumerated 232 functions on Apple M4. A first probe without explicit SDK
failed to load the Swift standard library; the corrected probe exited zero.

The isolated T7 artifact is under
`/Volumes/T7/aegis-360-items/build/mlx-swift-lm-stage-a-3.32.3-v5-shaders/`.
Its `status.json`, `build.log`, ten AIR files and library are retained. An
isolated Xcode overlay under T7 was tried for build-system routing, but
`xcrun` and `xcodebuild` stalled in a license-status child and were stopped.
The original signed Xcode app was untouched. The native SwiftPM `MLXVLM`
target build succeeded separately, but did not package a metallib.

This is a compiler and Metal API load proof. It does not prove MLX resource
bundle integration, GPU operation, model loading or semantic inference.
