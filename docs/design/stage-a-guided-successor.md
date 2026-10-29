# Stage A guided-generation feasibility (2026-10-27)

## Question and boundary

Could the pinned local `MLXGuidedGeneration` and xgrammar source provide an
offline, schema-constrained successor after the first SmolVLM2 Stage A packet
returned prose instead of the frozen eleven-field JSON? This investigation
does not invoke the model, retry the packet, change the prompt, or authorize a
new diagnostic protocol. The failed smoke and its exact evidence are in
`../experiments/stage-a-first-real-smoke-2026-10-27.md`.

## Local evidence

The isolated T7 source tree at
`/Volumes/T7/aegis-360-items/sources/mlx-swift-lm-3.32.3` is clean at
`3b339ad6e3b3f44c8121ecff5131c7fd55e075e6`, but `git rev-list --count
HEAD` returns **1**. `Package.swift` defines a standalone
`MLXGuidedGeneration` target depending on `MLXLMCommon`, `MLXCXGrammar`, and
`MLX`; the C++ target directly compiles vendored xgrammar with Apple `-w`
warning suppression. Its `VERSION` describes upstream tag `v0.1.30` and SHA
`d476a48dcd8fa3b5afeddbe850e73bb3b1dcf505`, but no upstream tree
comparison has verified the vendored content. The prior source audit in
`../experiments/mlx-swift-lm-source-audit-2026-10-18.md` likewise leaves
vendored identity and full compile behavior open.

The network-denied local Trivy 0.70.0 scan wrote
`/Volumes/T7/aegis-360-items/build/stage-a-guided-feasibility-v1/scan/trivy.json`.
Its cached DB dates to 2026-07-31; it found zero language-specific files and
zero result rows, so it gives **no** vulnerability coverage of this Swift/C++
target. The network-denied Syft 1.44.0 CycloneDX scan wrote
`/Volumes/T7/aegis-360-items/build/stage-a-guided-feasibility-v1/scan/sbom.cdx.json`.
Its 15 components are workflow actions/files, with no xgrammar or target
dependency inventory. Semgrep failed at startup with `ca-certs: empty trust
anchors`; it did not scan. The Docker daemon is unavailable, so the audit
skill's first-execution container could not run. These results cannot be read
as clearance.

## Provenance correction and next experiment

The prior single-commit result came from a **shallow checkout**, not a
single-commit upstream repository. On 2026-10-27 the existing checkout was
deepened to 51 commits without changing its HEAD or working tree. A separate
T7 clone of upstream `mlc-ai/xgrammar` tag `v0.1.30` resolved to the vendored
SHA `d476a48dcd8fa3b5afeddbe850e73bb3b1dcf505` and contained 50 visible
commits. All 59 vendored C++/header/license/notice files compared byte for
byte with that upstream checkout. Its pinned DLPack submodule
`bbd2f4d32427e548797929af08cfe2a9cbb3cf12` supplied an identical
`dlpack.h` (10,258 bytes). The earlier single-commit stop conclusion is
**superseded** by these observations.

The guided target's dependency names and build hooks were read. A narrow
pattern scan of `MLXCXGrammar` and `MLXGuidedGeneration` found no process,
network, dynamic-load or shell execution call; the `fork` occurrences refer
to grammar matcher state, not an OS process. This does not replace a working
Semgrep scan or a target-covering CVE/SBOM scan. Docker remains unavailable;
the next first execution uses a T7-local build with macOS Seatbelt denying
network, and must be reported as that narrower isolation. No grammar or
model result has yet been observed.

The original frozen Stage A diagnostic protocol and failed output remain
unchanged. The next experiment is a **new** diagnostic, with these separate
checks in order:

1. Compile and exercise the grammar target without weights. Test the exact
   eleven-field schema, forbidden extra keys, malformed JSON, and the
   conditional abstention values. Record whether the library compiles the
   schema and whether its token mask actually excludes a prose prefix. A
   successful compile alone does not prove constraint enforcement.
2. Check the current adapter's chat template and generation API using
   model-free inspection. Distinguish prompt/role formatting, output
   extraction, token budget and schema enforcement before attributing the
   prose to the model.
3. Only after those gates pass, run a bounded, fresh-input model diagnostic
   with an exact new runner and stop limits for swap, thermal pressure, wall
   time and invalid output. Do not use the six frozen Stage A diagnostic
   packets to tune this route. A complete semantic evaluation needs a new
   predeclared labelled set and independent repeats.

### Frozen model-free gate

The exact input schema is
`prompts/sparse-story-stage-a-v1/raw-observation-schema.json`; the frozen
model-free test uses no private packet, image or model weight. Build the local
`MLXCXGrammar` and `MLXGuidedGeneration` targets from the pinned v4 T7 package
graph, with Swift package, scratch, cache, module cache and temporary paths on
T7, and network denied by Seatbelt. Run upstream `CXGrammarTests` and
`MLXGuidedGenerationTests` if the local dependency graph permits. Then run a
repository-owned probe against the exact schema with a fixed toy vocabulary.

Pass requires: both targets compile; the schema compiles; an allowed
`observed` object can reach grammar completion; a prose prefix and an extra
key are excluded by the token mask; malformed input is rejected; and the
repository validator independently accepts the resulting valid JSON. The
conditional abstention rule must be tested separately: if xgrammar cannot
enforce `if`/`then`, the adapter must retain the validator as a mandatory
postcondition and the grammar cannot be described as full-schema enforcement.
Record test counts, skips and exact output hashes. A compile failure,
unsupported schema keyword, missing tokenizer mapping or vacuous test is a
failed or inconclusive gate, never a pass.

### Frozen synthetic format smoke

After the guided adapter's model-free build and malformed-input gates pass,
run `scripts/run_stage_a_guided_format_smoke.py` **once**. It creates six
synthetic 960x540 four-quadrant PNGs and a canonical adapter request under
`/Volumes/T7/aegis-360-items/build/stage-a-guided-format-smoke-v1`.
The frozen model and prompt/schema roots are reused unchanged. The new
adapter uses greedy guided generation with `maxTokens=512`, then the repo's
strict raw-output validator. This tests **format integration only**; no
real-media semantic score can be claimed from colored rectangles.

The runner starts one fresh network-denied process with T7 home, temp and
cache. It samples swap, process RSS and system thermal state every two
seconds; it stops the exact owned process group at 120 seconds, swap delta
over 5 GiB, sampled process RSS over 8 GiB, serious/critical thermal state,
or monitoring failure. Pass requires normal exit zero, no stderr, at most
65,536 nonempty stdout bytes and a valid closed eleven-field observation
according to the repository validator. It records byte hash, elapsed time,
resource maxima and result without committing pixels or raw model text.
Any failure is recorded and diagnosed before a different test; this exact
synthetic smoke is never silently rerun.

The real-media semantic diagnostic is not frozen yet. Its fresh inputs,
schedule, resource limits and acceptance rule must be fixed before that
model invocation. The six original Stage A packets remain frozen and cannot
be counted as a pass of this new candidate.

### Model-free result

The local target and repo-owned toy-vocabulary probe compiled under the
network-denied T7 build. The first probe process terminated because the
probe asked xgrammar for a new mask **after** accepting EOS; that was a
probe error, and it produced no result. The corrected probe used the EOS
commit's termination value and exited zero. Its compact result at
`/Volumes/T7/aegis-360-items/build/stage-a-guided-feasibility-v2/probe-result-v2.json`
has SHA-256
`c37813343e3816e19468a9b406689833ff0f87ce736fcdddeef94fe8482e1283`.
It reports schema compilation, opening brace allowed, prose first byte
excluded, complete observed object accepted, extra key rejected and
truncated JSON rejected. It also reports `bad_abstain_rejected=false`:
xgrammar accepts an abstention object violating the schema's `if`/`then`
condition. The repo's independent semantic validator and prompt-schema
tests passed 11/11 focused cases, including canonical abstention checks.
Therefore grammar controls JSON shape but **cannot replace** the validator.

The separate weight-free probe using the frozen SmolVLM2 tokenizer reports
49,280 vocabulary entries and EOS ID 49,279. Its real token IDs permit an
opening brace, exclude a prose prefix, and accept a complete valid observed
object through EOS. The result is at
`/Volumes/T7/aegis-360-items/build/stage-a-guided-feasibility-v2/tokenizer-result.json`
with SHA-256
`f02355b092b476b7281466a7f75ddbd4c791871c75f37c6fced48bc35f8f2d08`.
This establishes tokenizer/grammar compatibility for one valid path, not a
model integration or semantic pass.
The existing `smol_processor_smoke.swift` already checks that the frozen
system prompt survives tokenization, the six synthetic frames reach the
processor, and 486 image tokens are present. `StageAAdapterMain.swift`
uses `container.generate` with `maxTokens: 512`, `temperature: 0`, and
`seed: 0`, then validates only after output. It does **not** use
`MLXGuidedGeneration` or apply a token mask. This identifies an adapter
usage gap consistent with the prose output; it does not prove that a guided
adapter will preserve semantic accuracy or fit memory.

### Synthetic format smoke result

The frozen one-shot smoke on six synthetic four-quadrant rows exited zero
after 18.199 seconds. It emitted 405 stdout bytes, no stderr, and the repo
validator accepted the closed eleven-field object including the conditional
abstention rule. Raw stdout SHA-256 is
`a2ac43a0da546c1c5bf5136c3fd72ed9a0763f363cb45cfa5106759ae5a90464`;
the raw content and generated PNGs remain only under
`/Volumes/T7/aegis-360-items/build/stage-a-guided-format-smoke-v1/`.
The runner result records a baseline swap of 6,993,802,691 bytes and a
sampled peak of 11,337,665,085 bytes (increase 4,343,862,394 bytes), sampled
process RSS peak 701,005,824 bytes, child `ru_maxrss` 759,529,472 bytes,
and nominal thermal state throughout. Those RSS measures omit much of the
unified-memory pressure; the large swap rise is the stronger operational
signal. The smoke establishes **format integration**, not semantic accuracy,
repeatability, or acceptable sustained cost.

### Resource-complete successor gate

The first guided adapter did not expose MLX allocator peak memory. For a
real-media result that could satisfy the Stage A performance contract, the
separate v2 adapter adds an exclusive, fsynced, numeric-only metrics file
under its T7 `TMPDIR`. It records `Memory.peakMemory` (peak active MLX bytes)
plus final active and cache bytes, with the peak reset before model load.
This is distinct from OS process RSS and swap. The v2 runtime must be built
and admitted as an exact asset tree, and the retained synthetic cases must
be rerun for that exact binary. Its own one-shot synthetic format/metrics
smoke is `scripts/run_stage_a_guided_metrics_smoke.py`, with the same 120-second,
5-GiB swap delta, 8-GiB sampled RSS, nominal/fair thermal and strict-output
limits. Pass additionally requires the private metrics sidecar to have the
closed numeric schema. No result from the v1 binary transfers automatically
to v2b.

The final v2b build's exact runtime tree is
`c5aab63be1a005c2a554b7438cb172a127c3eafb7940a6b93ef8d7753a96db0e`.
An earlier v2 build copied a metrics source that required a trailing slash in
`TMPDIR`; the retained launcher does not provide one. That binary was not
used for inference and is not an admitted runtime. v2b fixes this path check.
Its retained suite passed 37/37 synthetic cases with `authority=false` in
201.073 seconds; the result is under `/Volumes/T7/aegis-360-items/build/sgc3/`.
Its one-shot synthetic format/metrics smoke also passed: 18.315 seconds,
normal exit, 405 stdout bytes and no stderr. The output SHA-256
`a2ac43a0da546c1c5bf5136c3fd72ed9a0763f363cb45cfa5106759ae5a90464`
matches v1's output for the identical synthetic input. MLX peak active was
5,139,256,118 bytes and final MLX cache was 1,695,296,844 bytes. Sampled
swap rose from 6,454,247,424 to 10,867,043,205 bytes, an increase of
4,412,795,781 bytes; thermal stayed nominal. Sampled process RSS peaked at
770,981,888 bytes, which is not a unified-memory total. The result and
private metrics sidecar remain under
`/Volumes/T7/aegis-360-items/build/stage-a-guided-metrics-smoke-v1/`.

The v1 binary's retained coordinator and isolation suite completed 37/37
expected synthetic cases with `authority=false` in 203.42 seconds. Two
earlier attempts produced zero observations: the first exceeded macOS's
Unix-socket path limit in its scratch name; the second was rejected by a
guard pinned to the old adapter tree. The guard now admits only the exact
old, v1 guided, or v2b guided `(entrypoint, root_tree_sha256)` pair, with
mismatch tests.
The successful result is under `/Volumes/T7/aegis-360-items/build/sgc2/`.
This synthetic suite says nothing about real-media semantic accuracy.

### Frozen real-packet operational smoke for the guided candidate

After the v2b format/metrics smoke and exact runtime synthetic gate pass,
`scripts/run_stage_a_guided_real_smoke.py` selects presentation ordinal 1
from the already published six-packet media gate. This is the Skiing packet
whose earlier **unconstrained** run produced prose. The treatment here is a
different adapter/decoder candidate; the frozen prompt, model assets and
media remain unchanged. It is recorded as a new guided-candidate smoke, not
a retry or replacement of the old Stage A result and not one of the two
complete six-packet runs. The model worker receives no source name, label,
prior output, repository or network path through the retained launcher.

The retained launcher enforces its 120-second limit. A separate monitor
samples the exact launch-ledger process every two seconds and stops only
its verified process group if swap rises over 5 GiB from baseline, sampled
RSS exceeds 8 GiB, thermal state reaches serious/critical, or monitoring
fails. The result is valid only with normal retained completion, a closed
eleven-field output accepted by the repo validator, the numeric-only MLX
peak sidecar, and complete wall/swap/RSS/thermal records. The selected raw
output, media and metrics remain on T7. A failed operational smoke stops
scope expansion for diagnosis; a valid one permits a separately frozen
two-run six-packet semantic evaluation.

### Frozen guided Stage A known-label evaluation

If the guided real-packet smoke is operationally valid, the same v2b runtime
and unchanged prompt/model/media execute exactly two independent serial runs
over the six previously frozen diagnostic packets in their canonical
presentation order. Each packet gets a fresh retained process group and
scratch directory: twelve complete-run invocations total. The smoke is
separate. The parent alone maps each selected private packet hash to the
predeclared class sequence: Old Ghost 205.6 `story_change`, Old Ghost 132.4
`no_semantic_change`, Skiing 200 `story_change`, Skiing 297
`no_semantic_change`, Skiing 327.25 `capture_artifact`, and Skiing 386.5
`no_semantic_change`. The presentation order is HMAC-derived and may differ
from that listing; labels never enter the adapter request or model process.

The exact per-invocation limits, measurement and output checks are those of
the guided real smoke above. Each run records exact raw-output hashes,
wall time, sampled RSS, MLX peak active bytes, swap and thermal state. A
complete result is `pass` only if all twelve invocations are valid, both
raw outputs for each matching packet are byte-identical, and all six classes
match their known labels in both runs. A complete but incorrect or
nonidentical result is `reject`; missing invocation, output, resource
measurement or lineage is `invalid`/`inconclusive` as appropriate. A resource
stop or operational failure ends the run without automatic retry and records
the unexecuted cases explicitly. This is a known-label feasibility test; it
does not measure generalization or blind viewer preference.
