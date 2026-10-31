# Stage A semantic error successor (2026-10-31)

## Status and boundary

This is an unsettled experiment design, not an ADR or a model-selection
decision. The guided v3 candidate passed format and repeatability but failed
3/6 known labels. The six diagnostic packets are exposed; no new treatment
may claim generalization from them. See
`../experiments/stage-a-guided-error-localization-2026-10-31.md`.

## Frozen synthetic sensitivity check

Before another real-media inference, run two fresh, separately stored local
synthetic probes using the same pinned v3 adapter, SmolVLM2 weights, prompt,
schema, six-row request shape, 960×540 image size and greedy guided decoder.
Use the existing network-denied T7 synthetic runner's 120-second wall,
5-GiB swap-rise, 8-GiB sampled RSS and serious/critical thermal stops,
private home/temp/cache and numeric MLX sidecar checks. No download occurs.
Each variant uses a new T7 output directory and is invoked at most once.

- `static`: six byte-identical four-color quadrant images, with one fixed
  light rectangle. There is no temporal image change.
- `palette_step`: the same fixed rectangle and geometry; the palette changes
  after row 3, identically across all four quadrants. There is no object or
  viewpoint motion.

Before launch, hash the six images and canonical requests; after launch,
record output byte hashes, strict-validator status, parsed observation values,
wall/swap/RSS/thermal/MLX measures and unexecuted count. This is a
**sensitivity diagnostic**, not an event-accuracy benchmark. A useful
positive observation is that `static` does not claim a temporal change or
artifact, while `palette_step` marks exposure/palette change without
inventing story or capture artifact. If both outputs collapse, the test
shows failure to distinguish these artificial inputs under this prompt and
decoder; it does not prove that weights ignore all images. Any operational
failure stops the experiment without an automatic retry.

## Real-label successor

Separate two target scales that Stage A mixed:

1. **Center event:** the intended label is supported or refuted by rows
   immediately before/after the center. Do not infer it solely from far
   ±15-second context. A new reviewer explicitly records `center_supported`,
   `center_refuted` or `center_unassessable` before assigning a class.
2. **Broad progression:** early and late rows may differ, but an exact center
   is not claimed. Evaluate this separately as a segment/chapter relation,
   not as a center event.

Build a fresh, source-diverse review set from already acquired benchmark media
and exclude all six Stage A centers and their ±30-second neighborhoods.
Select candidate centers deterministically from published signal timelines
and a fixed control lattice before inspecting frames. Keep source/time,
proposal/control role and expected class out of adapter input and reviewer
presentation. An independent human review supplies center support and class
labels with explicit abstention; two reviewers or an adjudication step resolve
disagreement. No agent/model answer may be called owner ground truth. Keep
review PNGs and raw labels on T7; the repo may store only licensed,
path-free hashes, protocol and aggregate findings. Freeze the new treatment,
selection and scoring rule before inference. Balance story, no-change and
artifact cases where supported; report any class with no independently
labelled positive as untested. Pass requires correct class on every eligible
case plus two byte-identical serial runs, operational gates and resource
records; otherwise reject/invalid/inconclusive according to the prior Stage A
precedence. This is a bounded gate, not final generalization. The existing
Stage B protocol remains gated on an eligible Stage A successor.

## Cursor review route

The owner prefers Cursor Grok 4.7 High for an independent review. The CLI
currently reports no login; the app shows an account but an isolated
workspace route was not established. A public-only review brief is staged
locally with a file hash. No private packet, media, weight, untracked file or
prompt has been sent. Use Grok only after verifying the exact account/model,
read-only mode and isolated input scope. Any nonpublic payload needs the
repo's fresh send code bound to its manifest and destination. Its findings
must be independently checked against local evidence.

### Unguided control after the collapsed guided result

The frozen synthetic arms completed operationally but emitted identical wrong
observations, including static frames. Before changing the prompt or model,
run one bounded unguided control per exact synthetic input set using the
previous pinned adapter runtime. Keep request, images, model, prompt and
network-denied T7 environment identical; only decoder changes. Record each
raw output's byte hash/length and whether the outputs differ. The old adapter
is not required to emit closed JSON for this control. Enforce the same 120-s,
5-GiB swap-rise, 8-GiB sampled RSS and serious/critical thermal stops, no
stderr, and fresh output roots. Run each arm once, without retry. If the
unguided outputs differ while guided outputs are identical, inspect grammar
choice bias or guided loop integration before blaming image preparation. If
both paths collapse, inspect vision embeddings and prompt semantics next.
Neither branch proves general model quality or authorizes a class-rule patch.

### First-token multimodal logit control

The two unguided outputs differed and the static arm explicitly described no
motion; both guided outputs remained identical false artifact claims. Before
interpreting this as a grammar bug, measure the model's raw first-next-token
logits immediately after the same `container.prepare(input:)` and
`context.model.prepare(...)` used by the guided loop. Build a separate
network-denied, T7-only readout executable from pinned source without editing
upstream. Feed the *exact existing* static and palette-step synthetic bundles,
verify input/request image hashes, and run each once under the same 120-s,
5-GiB swap-rise, 8-GiB RSS and thermal stops. Record only the SHA-256 of
float32 last-position logits, vocabulary length, top-token ID and hash of
prepared prompt token IDs; no logits or pixels leave T7.

If prompt-token hashes match and logit hashes differ, the image path affects
first-token model computation; focus the next investigation on how the guided
grammar selects enum values and on prompt semantics. If logits match, inspect
the model's vision-feature merge and preprocessing before any prompt change.
An operational failure or mismatched text prompt is inconclusive. This is a
model-path diagnostic, not a Stage A semantic pass, and it does not rerun
private diagnostic packets.

### Exact grammar alternative reachability

The first-token logits differ but the guided outputs collapse. Before changing
prompt wording or decoder policy, compile the existing tokenizer grammar probe
against the frozen schema and installed model tokenizer. Check three complete
objects independently: the previously accepted no-change observation, one
with `activity_relation=changed`, `setting_relation=changed` and
`transition_support=supports`, and one with
`capture_or_projection_artifact=present`. Each must be admitted token by token
through EOS. This is a model-free reachability check, not a ranking test. If
all are accepted, grammar exclusion does not explain the collapse; inspect
guided candidate rankings and prompt semantics next. If an alternative is
rejected, localize its first rejected token before interpreting model choice.

All three complete alternatives passed the exact tokenizer/schema probe on
2026-10-31. The next bounded diagnostic is a read-only trace of the guided
decoder's legal-token rankings at the first discriminating value token in
each field, on the already frozen static and palette-step synthetic bundles.
Record token IDs, decoded token fragments, raw and masked scores, the applied
bias zone, and whether fast-forward forced any surrounding tokens. Do not
log raw frames, full logits, credentials or private packet output. A ranking
trace can locate selection behavior, but it is not an accuracy gate.
