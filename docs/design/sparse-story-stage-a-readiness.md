# Stage A smoke readiness

Status: local prompt/schema contract prepared; no Stage A invocation

The synthetic adapter gate passed at `BinHsu/aegis-360@4478a4d` with exact-SHA
`handoff-contract` CI run 39021685116. Its synthetic fixture proves runner
operation only. Stage A needs one genuine packet and a normal-mode local
semantic adapter before a smoke can run; the two full six-packet runs follow
only after that smoke. The frozen protocol is
`docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md`, especially
its private packet lineage, isolated runner and Stage A sections. ADR 0010 keeps
semantic evidence sparse and prohibits the model from commanding the camera.

## Local evidence, 2026-10-17

- The installed SmolVLM2 2.2B MLX BF16 `model.safetensors` has the size and
  SHA-256 in `model-manifests/manifest.toml`. This verifies that one weight leaf,
  not the complete closed model asset tree or runtime compatibility. The local
  Old Ghost Road and Skiing original media also match both size and SHA-256 in
  `benchmarks/manifest.toml`; no new asset was acquired.
- Old Ghost Road and Skiing originals and earlier experiment outputs exist under
  the configured external data root. No real successor private packet was found.
  The current private packet API validates supplied structure; it does not
  derive source lineage. Old Ghost event timelines and a cardinal grid exist;
  the Skiing successor timeline/grid do not yet exist.
- `prompts/sparse-story-stage-a-v1/` now contains a label-neutral prompt and
  strict raw-observation JSON Schema. Its three contract tests pass, including a
  changed-enum negative control. A local JSON Schema engine accepts the canonical
  abstention and rejects an altered abstention. No model received the prompt.
- `src/aegis360/sparse_story_runner_contract.py` lists Stage A run kinds but
  derives a live aggregate only for the synthetic gate. The current private
  schedule is synthetic only. No normal-mode VLM adapter is implemented.

## Next implementation boundary

The dependency-free `sparse_story_stage_a_lineage.py` now rebuilds six
ordered private packets from a frozen manifest and caller-supplied source,
timeline and grid evidence. It hashes exact raw manifest/timeline/grid JSON
bytes, rejects duplicate keys and nonfinite values, and checks selected
proposal IDs/timestamps, rational centers, cardinal view order, row offsets and
packet hashes. A controlled mutation is accepted by the old shape validator
but rejected by exact lineage. Five focused tests and full portable discovery
(919 tests, 97 skipped) pass. The manifest schema is explicitly `synthetic.v1`:
this is a preflight contract, not a real source or semantic claim.

The new `sparse_story_stage_a_timeline_proof.py` exact-rebuilds a supplied v2
timeline from raw grid, scene-candidate and optional reaction JSON bytes. It
rejects a changed event ID even when the timeline hash is recomputed. Four
focused tests pass, and the four existing Old Ghost v2–v5 timeline artifacts
each rebuild from their paired grid/candidate files. This proves derivation
from those supplied upstream JSON files, not that the scene candidates were
extracted correctly from source pixels. Full portable discovery now runs 923
tests with 97 skips.

The real-input in-memory preflight derives a Skiing grid and zero-event
timeline from the existing 10-fps scene-events JSON. It combines Old Ghost v5
at 205.6 seconds as one proposal with five controls. Six private packets and
six adapter projections rebuild; the proposed manifest SHA-256 is
`5b5cfa39fa0d1cb0600ccca2f8c029d8ad16f4449d35f4e018e8fffc5a98a465`.
The Skiing zero-event result exposes a cheap-signal recall gap, not a story
classification. The deterministic builder at
`scripts/build_stage_a_preflight_bundle.py` passes a real-input no-write dry
run. It rehashes both source files before and after packet preparation,
exact-rebuilds the Old Ghost timeline, derives the Skiing zero-event timeline,
and prepares fourteen bundle files. The stable salt is a mode-0600 local
ignored file; it is never in the bundle or report. The dry-run adapter-index
SHA-256 is `41fe1ee21e1c7ad0c3325842222826e61a5953dc35d39309d3c54cbe49f841bb`.
Code `送 745` authorized publication of the exact fourteen-file bundle to
external storage. Every published file was read back against the dry-run
hashes; the directory is mode 0700 and the files are mode 0600. Next make
sanitized PNG inputs. No model has run.

The local `sparse_story_stage_a_render.py` defines a bounded, serial FFmpeg
row acquisition path. The bundle-facing runner first exact-rebuilds and compares
all fourteen published preflight JSON files. It checks source hashes before and
after rendering, uses private row time and four cardinal views, and passes each
960x540 RGB PNG through the closed sanitizer. Two independent real-media runs
produced the same 36-image tree and result hash; the canonical external T7
publication matches both. Three representative images were visually inspected.
See `docs/experiments/stage-a-media-preflight-2026-10-18.md`. Two misplaced
local pixel-bearing verification bundles were removed after exact replacement
verification and owner authorization. Full portable
discovery passes 946 tests with 97 skips on macOS 27.0.1. The host test now
expects fail-closed rejection of `/usr/bin/sandbox-exec`'s new ARM64 subtype;
native invocation authority remains closed on this OS. No model has run.

The runner's frozen v1 asset rule requires a directly executable ARM64 Mach-O
entrypoint. The installed MLX Python script cannot be passed as that runtime.
The official MLX Swift LM project includes a SmolVLM2 implementation and a
local-directory loader, making a native Swift adapter a plausible candidate,
not a verified one. Its source/dependencies are not installed or authorized by
this checkpoint; pin and audit them before acquisition. Do not relax the
isolation or model-asset rule by treating a Python wrapper as a native adapter.

Primary upstream references:
- https://github.com/ml-explore/mlx-swift-lm/blob/main/Libraries/MLXVLM/Models/SmolVLM2.swift
- https://github.com/ml-explore/mlx-swift-lm/blob/main/Libraries/MLXLMCommon/ModelFactory.swift

## Bounded native-adapter source review plan

Candidate: official `ml-explore/mlx-swift-lm` tag `3.32.3`. The upstream tag,
commit, dependency graph, license and compatibility must be verified from the
acquired source; a release listing is not a local source audit. Swift 6.4 and
Swift Package Manager are available through Command Line Tools, but an Xcode
app is not selected. Neither fact proves this package will compile here.

The first network step, if the owner explicitly requests it, is a source-only
fetch of that tag into an isolated scratch directory under `/private/tmp`.
Record the resolved full commit and tree hashes, remote URL, license, source
inventory, package manifest, declared dependency revisions and any build or
plugin hooks. Do not run `swift build`, resolve packages, execute an example,
load the model, or contact a model registry during this step. Run local static
scanners against the acquired tree where useful; report their coverage and
limits. Any later dependency acquisition or execution needs a separate bounded
review of the exact graph and offline behavior.

Keep the current fail-closed macOS 27.0.1 native backend proof unchanged until
a host-specific ABI and invocation review establishes the new subtype's
meaning. Stage A semantic smoke stays blocked until both that proof and an
audited adapter are ready. Media and model assets stay under T7; source audit
scratch stays outside the checkout and contains no benchmark pixels.

That source-only step completed with owner approval on 2026-10-18. The resolved
commit and tree, declared graph, source findings and scanner limits are in
`docs/experiments/mlx-swift-lm-source-audit-2026-10-18.md`. Dependency sources,
build and invocation remain outside the completed scope.
