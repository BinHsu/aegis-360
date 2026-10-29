# Current handoff

Updated: 2026-10-30T05:17:27+08:00
Repository: aegis-360
Branch: main
Baseline commit: 2e2b8e1
Remote status: local `origin/main` is `621c195`; local main is ahead and no aegis push is authorized in the current task.
Working tree at checkpoint: expected clean after this local milestone commit; verify with Git before editing.

## Objective

Build the offline 360-video auto-director for ordinary viewers on the fanless
M4 MacBook Air. The current bounded gate is a sparse Stage A semantic adapter
for six private packets. The model emits closed event observations but cannot
command the camera; global planning owns viewpoints (ADR 0010). The Skiing
RGB and color-independent structural chapter proposals were rejected.

## Last completed milestone

The guided v2b adapter built offline on T7, passed 37/37 exact-runtime
synthetic cases, and produced a closed eleven-field result in one synthetic
model smoke. It recorded MLX peak active memory and swap; the latter rose
4.41 GB. The same synthetic output bytes match v1. A toy-vocabulary probe
found xgrammar does not enforce the schema's conditional abstention, so the
repo's strict validator remains mandatory. See
`docs/design/stage-a-guided-successor.md`.

## Repository state

- Latest local milestone: guided v2b source, exact runtime evidence and
  frozen real-evaluation scripts (resolve the commit with `git log -1`). The
  shallow-checkout blocker at `2e2b8e1` is superseded.
- T7 products and logs
  remain outside Git.
- The last published exact-SHA green CI claim is for `4b78e1a`. CI for the
  current local commits has not run. No Stage A build has been published.

## Verified

- Xcode 27.2 RC (27B48) and Metal Toolchain 27B47 are installed on T7;
  Xcode first launch and license acceptance completed. The original signed
  app is intact. The system retained about 881 MiB of Apple MobileAsset data.
- The direct mounted Metal compiler works. Xcode's compiler stub still says
  the component is missing; an isolated T7 Xcode overlay stalled during
  license status and is not a working build route.
- Full portable repository discovery before toolchain work ran 947 tests
  with 97 skips and no failures. Current toolchain work ran focused checks.
- Real-media Stage A preflight produced six private packets and 36 sanitized
  960x540 PNGs with matching repeat hashes on T7; six selected PNGs entered
  the failed model smoke.
- `MLXVLM` target build, manually linked Metal library and MLX GPU array add
  passed offline; see `docs/experiments/mlx-swift-metal-library-v5-2026-10-23.md`.
- The SmolVLM2 2.2B local asset tree matches its cached revision inventory;
  see `docs/experiments/stage-a-model-asset-tree-2026-10-23.md`.
- The MLX Swift LM shallow checkout was deepened to 51 commits. Vendored
  xgrammar's 59 files and pinned DLPack header match upstream byte for byte.
  Trivy/Syft still do not cover the Swift/C++ target; Semgrep could not run.
- The guided target built offline on T7. Toy and installed SmolVLM2 tokenizer
  probes admit valid JSON and exclude prose. The toy probe shows xgrammar
  accepts a bad conditional abstention, so the repo validator remains required.
- Guided v1 and v2b binaries each passed 37/37 retained synthetic cases;
  their separate synthetic model smokes emitted byte-identical valid output.
  v2b measured MLX peak active 5,139,256,118 bytes, swap delta
  4,412,795,781 bytes, and nominal thermal state over 18.315 seconds.

## Rejected

- Skiing RGB-persistence and the color-independent structural successor as
  chapter detectors. Do not retune the frozen comparisons.
- Treating a successful SwiftPM target build as Metal packaging or inference
  proof; treating the Xcode overlay as a supported toolchain.
- `EventSource` 1.0.0 adoption: its two-commit history starts with a
  complete implementation, triggering the supply-chain-audit stop signal.
- `swift-collections` 1.0.0 for this Swift 6.4 build: the bounded v2 attempt
  failed on Sendable checking; the v3 build used pinned 1.7.2.
- The earlier single-commit source rejection is superseded: it was a shallow
  checkout. Do not repeat that claim.

## Pending

The original real one-packet unconstrained smoke remains invalid prose and
4.23 GB swap increase. The new guided candidate has only synthetic model
output so far; no real-media semantic or repeatability result exists. The
next frozen gate is one guided real-packet operational smoke with exact
process monitoring, followed only if valid by two serial six-packet runs.
Trivy/Syft did not cover the Swift/C++ target and Semgrep could not scan;
source provenance and bounded runtime behavior do not prove absence of CVEs.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 scripts/check_handoff.py
git status --short --branch
python3 scripts/run_stage_a_guided_real_smoke.py
```

The script creates a new T7 output root and runs once after checking the
fixed runtime/model/media inputs. If it fails, inspect its durable result
before any new invocation. It is a new guided-candidate smoke, not a pass of
the old frozen protocol.

## External artifacts

Set `AEGIS_DATA_DIR` to the approved T7 project root locally. Pinned
third-party sources are under its `sources/` area; MLX v4, shader v5 and
GPU-smoke v6 artifacts are under `build/`. Media, frames, model weights,
scratch and compiled products stay there and are never committed.

## Active agents

No delegated work or background job is running.

## Safety and claims

- One selected real packet reached the old adapter and failed the closed
  schema. Two synthetic packets reached guided adapter versions and passed
  format validation; no real-media guided semantic outcome exists.
- Build, format, Metal API load and asset hashes prove their bounded checks;
  they do not establish VLM semantic accuracy or sustained performance.
- The dotfiles policy push was completed separately under code `520`; this
  does not authorize an aegis remote push.
- Git history is the archive; this file describes the current work state.
