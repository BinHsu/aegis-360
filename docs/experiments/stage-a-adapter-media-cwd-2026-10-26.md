# Stage A native media path smoke

Date: 2026-10-26. Host: Apple M4 MacBook Air, macOS 27.0.1, Xcode 27.2 RC (27B48). A Foundation/ImageIO ARM64 executable was compiled with the T7 SDK; its source snapshot, cache, synthetic PNGs, product and logs stayed under `/Volumes/T7/aegis-360-items/build/`. Compile and cases ran under `sandbox-exec` network denial. No model or private pixels were used.

The retained launcher is designed to set the child's current working directory from its verified bundle descriptor. The frozen request supplies only six bundle-relative media paths. `StageAResolvedMedia.resolve` uses that cwd and those exact parsed paths, requires each leaf to be a regular single-link file, decodes it as a single PNG, and checks 960×540 dimensions. It returns local URLs for later `UserInput.Image` construction. The coordinator still owns exact bundle identity, hashes, ancestor checks and pre/post invocation proof; this helper does not replace those checks.

The synthetic stand-in bundle contained six generated 960×540 PNGs. The valid request decoded all six. Four independent copies changed one row: missing file, 2×2 PNG, corrupt PNG bytes, and symlink. Each exited 3 with only `invalid adapter media` on stderr. The five-case v1 stage passed in 2.753 seconds. Source hashes and exact logs are retained at `/Volumes/T7/aegis-360-items/build/stage-a-adapter-media-v1/`.

This is a cwd-relative read and format check, not a test of the retained launcher, private asset manifest, confinement, model loading or inference. No model ran.
