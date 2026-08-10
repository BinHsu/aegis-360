# SmolVLM2 500M context gate — 2026-08-11

Status: Rejected after prompt-only and schema-constrained gates

## Setup

- Hardware: fanless MacBook Air M4, 16 GB unified memory.
- Model: MLX BF16 conversion revision
  `fa57db46815177fbdfd65cc85a2b3416a8332268`.
- Runtime: Python 3.12.13, MLX 0.32.0, MLX-VLM 0.6.12, torch 2.13.0,
  torchvision 0.28.0.
- Input: accepted four-second conversation-group auto render, sampled as
  ordered images because the processor reported no native video support.
- Policy: model text is untrusted and must pass scene-context v2 unchanged.

The first sandboxed MLX import aborted because Metal was unavailable to the
restricted process. The same import succeeded with hardware access; this was
an execution-environment issue, not model corruption. The first processor load
then failed closed until the missing torchvision dependency was installed.

## Results

1. Eight frames, verbose JSON prompt: semantic class/scope were
   `conversation`/`group`, but the model invented `window:1` and emitted flags
   as an array. Cold run: 55.27 s, maximum RSS 1,664,958,464 bytes, zero swap.
2. Four frames, exact JSON skeleton: copied pipe-separated alternatives and
   truncated before a complete object. Run: 11.05 s, maximum RSS 2,448,326,656
   bytes, zero swap.
3. Four frames, eight-token closed code: returned only `1,2,3`. Run: 8.39 s,
   maximum RSS 2,439,872,512 bytes, zero swap.

Follow-up inspection found MLX-VLM 0.6.12's server/library path does support
`llguidance` JSON-schema constrained decoding even though the `generate` CLI
does not expose it. Two direct-library runs corrected the earlier assumption:

4. Four frames with a strict schema produced valid JSON, but selected
   `coordinated_activity/context/forward:context` and falsely marked audio
   evidence present despite receiving only images. Model elapsed time was 8.53
   seconds, MLX peak memory 2.93 GB, maximum RSS 1,251,934,208 bytes, zero swap.
5. Eight frames with class definitions and audio fixed to `unknown` still chose
   `coordinated_activity`, paired `group` scope with the incompatible
   `forward:context` candidate, and marked every visual flag unknown. The
   scene-context validator rejects that cross-field mismatch. Model elapsed
   time was 13.08 seconds, MLX peak memory 4.51 GB, maximum RSS 2,173,272,064
   bytes, zero swap.

macOS `time -l` also reported peak-memory-footprint values around 5.1–7.3 GB;
that metric is not interchangeable with maximum RSS. Neither showed swap.

## Decision

The M4/16 GB feasibility hypothesis passes for this bounded workload, and the
first response suggests useful coarse scene semantics. Instruction/output
compliance fails all three prompt-only protocols. Grammar guarantees JSON and
enum syntax but not correct semantics or valid scope/candidate relationships;
the closed importer still rejects the result. Do not weaken cross-field
validation or spend more time tuning this 500M model. A larger model requires a
separate candidate and explicit acquisition decision.
