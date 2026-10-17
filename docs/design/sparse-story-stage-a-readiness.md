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
  not the complete closed model asset tree or runtime compatibility.
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

Next, verify source bytes against the declared source SHA-256 and exact-rebuild
each v2 timeline from its upstream scene/reaction evidence. Then build the real
Skiing timeline/grid and six diagnostic packets, and only after their lineage
is verified make sanitized PNG inputs. No model has run.

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
