# Stage A guided v3 known-label result — 2026-10-30

## Question and protocol

Does the pinned SmolVLM2 2.2B, frozen six-frame Stage A prompt/media and
MLX-guided decoder produce closed, repeatable observations with the six
predeclared event classes? The original unconstrained packet produced prose.
The guided successor is a separate diagnostic. The treatment and two serial
six-packet schedule were frozen in `../design/stage-a-guided-successor.md`.
The private input, image bytes, output text and model weights remain on T7.

## Operational corrections

The guided v2b real smoke returned closed JSON but was invalid because its
metrics sidecar violated the retained private-TMPDIR empty postcheck. The v3
runtime moved that sidecar into the allowed scratch root. Its exact runtime
tree hash is `5e8f4a9e92432a552d65b6dfc0eebc77848b24e316fdc221c67e4ca93dc51184`.
The v3 retained 37/37 synthetic cases passed, `authority=false`; one synthetic
model smoke returned valid 405-byte JSON with an empty private TMPDIR.

A subsequent real smoke isolated one macOS sandbox-extension warning on
stderr naming only the pinned runtime directory. The revised candidate
transport accepts exactly that 137-byte message; any other stderr still
fails. The exact-byte exception and its discriminating test were fixed before
the final real smoke and twelve labelled invocations. Earlier operational
abstentions are not counted. The final one-packet smoke completed and returned
`no_semantic_change` in 40.140 seconds with passing retained postcheck.
Its T7 status is under `build/stage-a-guided-real-smoke-v5/`.

## Measured result

The final schedule under `build/sga4/` completed **12/12** invocations,
0 unexecuted. Both runs produced byte-identical raw outputs for each packet.
Every output was closed JSON, accepted by the strict repo validator, and had
normal retained completion. The six event classes and known labels were:

| Presentation ordinal | Expected | Both runs observed | Correct |
|---|---|---|---|
| 1 | `no_semantic_change` | `no_semantic_change` | Yes |
| 2 | `story_change` | `capture_artifact` | No |
| 3 | `story_change` | `capture_artifact` | No |
| 4 | `capture_artifact` | `capture_artifact` | Yes |
| 5 | `no_semantic_change` | `no_semantic_change` | Yes |
| 6 | `no_semantic_change` | `capture_artifact` | No |

The candidate matches **3/6** labels per run. Its predeclared pass rule
requires 6/6 plus byte repeatability, so the outcome is **reject**, despite
6/6 byte-identical repeats. The maximum per-invocation sampled swap rise was
353,433,027 bytes, maximum sampled child RSS 1,164,148,736 bytes, and maximum
MLX peak active 5,139,256,118 bytes. The sum of invocation wall times was
363.344 seconds, mean 30.279 seconds; thermal was nominal or fair. These
are per-run measurements, not a cold-start or total unified-memory profile.

Observed raw observations for ordinals 2, 3, 4 and 6 all marked
`capture_or_projection_artifact=present`, `viewpoint_change=present`, and
`exposure_or_palette_change=present`; ordinal 3 differed in its byte-level
observation but mapped to the same wrong class. The synthetic color-quadrant
smoke also mapped to `capture_artifact`. This pattern suggests the model or
prompt may over-attribute visible change to capture artifacts; it does not
establish whether the error comes from image preprocessing, instructions,
model capability, or the class derivation rule. No tuning was performed on
the frozen six packets.

## Interpretation and next step

Guided decoding solved the format failure and produced deterministic output
under this bounded protocol. Semantic accuracy remains insufficient for a
Stage A event source. Do not grant planner authority or report broad model
ineffectiveness. Next, inspect the actual image-token and preprocessing path
with model-free probes and an independent labelled holdout before changing
the prompt or thresholds. Any changed treatment needs a fresh protocol and
held-out evaluation; these six packets remain diagnostic, not training data.
