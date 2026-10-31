# Stage A guided error localization (2026-10-31)

## Question

Where do the three wrong known-label classes first diverge: packet evidence,
model observation, or the deterministic class rule? This is a post-result
diagnostic. The six packets are already exposed and are not held-out data.

## Observations

The two complete guided runs produced byte-identical outputs per packet. After
JSON parsing there are only **two distinct eleven-field observation objects**
across the six packets, although there are three raw byte hashes. The four
packets classified `capture_artifact` have identical field values. The two
classified `no_semantic_change` also have identical field values. Changing only
`capture_or_projection_artifact` from `present` to `absent` on any of the three
wrong outputs yields `abstain`, because the model also marked activity and
setting `same`, plus nuisance changes `present`. Therefore changing the class
rule's artifact priority alone cannot recover the known labels.

| Diagnostic packet | Label | Center-pair visual observation | Model fields and first supported divergence |
|---|---|---|---|
| Skiing 200 s | story change | At 199.75/200.25 s both rows show a skier on open snow. The station appears in the far row at 185 s; earlier human evidence explicitly did not claim an exact transition time. | Model says activity/setting `same` and artifact `present`. The six-row target mixes coarse chapter progression with a center event. The packet/label time scale is unresolved before scoring this as a center-boundary error. |
| Old Ghost 205.6 s | story change | At 205.35 s a confined forest path is visible; at 205.85 s a suspension bridge and river context is visible. This agrees with the prior independent human story-change label. | Model says activity/setting `same` and artifact `present`; the observation differs from visible center-pair evidence. |
| Old Ghost 132.4 s | no semantic change | At 132.15/132.65 s the mountain trail activity continues, with changing viewpoint/foreground. Far rows at 117.4/147.4 s show broader context differences. | Model says activity/setting `same` but artifact `present`, yielding the wrong class. The prompt may encourage broad early/late comparison for a local negative; the artifact claim is not established by the viewed center pair. |
| Skiing 327.25 s | capture artifact | Center rows visibly show stitch/stretch discontinuities. | `artifact=present` matches this bounded positive. |

The visual review used the retained six 960×540 four-cardinal composites per
packet on T7; media and raw output remain external. The packet center, row
roles and source times came from the exact preflight bundle. The label
provenance is in `structural-chapter-blind-replication-v1-2026-09-06.md`,
`skiing-gradual-chapter-proposals-v1-2026-09-06.md` and
`sparse-story-semantic-successor-v1-2026-09-07.md`.

## Assessment

A deterministic class-rule-only patch is not supported. The Old Ghost
205.6 case shows a genuine observation miss. The Skiing 200 case exposes a
label/time-scale mismatch that must be resolved before comparing a
center-local adapter. The Old Ghost 132.4 case is a false artifact claim or
an over-broad interpretation of context. The current evidence cannot
separate prompt semantics, square image resizing, model capacity, or guided
decoder value bias. A new controlled stimulus and an independent holdout are
needed; no treatment was changed or rerun on these six packets.

## Frozen synthetic temporal sensitivity result

The successor design froze two network-denied, one-shot synthetic runs before
inference. Both used the exact guided v3 runtime and six 960×540 PNGs. The
`static` arm's six image SHA-256 values were identical. The `palette_step`
arm had one identical image hash for rows 1–3 and another for rows 4–6;
geometry and the light rectangle stayed fixed. Both calls exited zero,
passed strict JSON validation, had empty private TMPDIR and numeric MLX
metrics, and stayed nominal thermal. `static` took 18.262 seconds with MLX
peak active 5,181,898,386 bytes; `palette_step` took 16.206 seconds with the
same MLX peak active. No invocation was skipped.

Both arms produced the **same 405 output bytes**, SHA-256
`a2ac43a0da546c1c5bf5136c3fd72ed9a0763f363cb45cfa5106759ae5a90464`,
identical to the previous moving-rectangle synthetic smoke. The parsed
observation falsely claimed viewpoint, foreground, palette and capture
artifact changes even for six byte-identical frames. These outputs are
operationally valid but fail the predeclared useful-sensitivity observation.
The result establishes a concrete prompt/decoder/model-path failure on
artificial stimuli. It does not by itself show whether raw vision embeddings
change with the pixels or whether the grammar/value selection dominates them.
The next discriminating control compares the same two input sets through the
previous unguided adapter without trying to score its prose as a valid Stage A
result.

## Unguided and first-logit controls

The pinned previous adapter ran once per exact synthetic bundle, with the
same resource stops and no operational failure. Its static output (414 bytes,
SHA-256 `529fd18fa581b7896fde8b1918de46de71780bfeb100eb0f46dd01bdd5bf834e`)
described repeated colored squares and no movement. Its palette-step output
(409 bytes, SHA-256 `55270b786f52de8ace1e87df7ff2884949299fdac6bf231b268abee7cc7a4acc`)
described different color schemes, though it misstated the number of frames.
These prose outputs are diagnostic only; neither is a valid Stage A result.
They differ where the guided observations were byte-identical.

An independently built first-token probe used the same prepared input path.
Both arms had 1,023 prompt tokens and the same prompt-token SHA-256,
`6f644c0fb36d2e4d01f668cf2f34c3c3961827d3c292c61e3fbb9fea11406526`.
The 49,280 float32 first-position logits differed: static SHA-256
`eace395572e7cac3bba360a93c9245347935df82f6fd2f0b6129b69e542432cc`;
palette-step SHA-256
`04711c3f042f2ec5130337deace962f3cf42c4ce6aa5719b9c5f8ea3408775aa`.
Both retained top token ID 378. Both calls completed once under the bounded
resource policy, with no stderr; thermal was fair. This establishes that the
different images affect the model's first generation computation under an
identical text prompt. It does not establish that the relevant enum choices
have different rankings after grammar masking.

The next discriminator is whether the exact tokenizer and JSON grammar
accept alternate complete observation values. An accepted alternative would
rule out a schema-level exclusion of those values, while leaving guided
selection bias and prompt semantics open. Neither synthetic arm supplies
real-media accuracy evidence. The six known-label packets remain diagnostics,
not a new holdout.

## Exact grammar alternative reachability

The model-free tokenizer probe was built offline on T7 from the pinned local
Swift packages, installed SmolVLM2 tokenizer and frozen Stage A schema. It
accepted three complete objects token by token through EOS: the baseline
`same`/`absent` observation, an alternative with activity and setting
`changed` plus `transition_support=supports`, and an alternative with
`capture_or_projection_artifact=present`. It also admitted an opening brace
and excluded an ordinary prose token. Vocabulary size was 49,280 and EOS
token ID 49,279. All checks returned true; no case was skipped.

The grammar therefore does not structurally exclude the alternate values
needed for a correct observation. This does not measure their constrained
logit rankings or prove the guided loop's later-token behavior. Combined
with differing first logits and unguided prose, the next diagnostic should
inspect candidate rankings at the actual field-choice positions under
guidance before changing model, prompt or class rule.
