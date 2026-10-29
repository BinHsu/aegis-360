# Current handoff

Updated: 2026-10-30T05:42:51+08:00
Repository: aegis-360
Branch: main
Baseline commit: 7234a04
Remote status: local `origin/main` is `621c195`; local main is ahead. No aegis push is authorized by the current task.
Working tree at checkpoint: guided v3 correction and measured-result milestone pending local commit; verify Git status before editing.

## Objective

Build the offline 360-video auto-director. The current bounded Stage A gate asks
whether SmolVLM2 can emit correct, closed event observations for six private
real-media packets. Global planning alone owns camera viewpoints (ADR 0010).

## Last completed milestone

The v3 guided adapter fixed a private-TMPDIR sidecar violation and pinned an
exact T7 runtime tree. Its retained host suite passed 37/37 synthetic cases,
`authority=false`, and its synthetic model smoke passed format validation. A
real diagnostic isolated a macOS sandbox-extension warning on stderr; the
revised guided candidate accepts only its exact 137-byte form. The final
one-packet real smoke completed. Two serial six-packet runs completed 12/12,
0 unexecuted, with byte-identical repeats, but only 3/6 known labels correct
in each run. The predeclared semantic gate **rejects** the candidate. See
`docs/experiments/stage-a-guided-v3-known-label-2026-10-30.md` and
`docs/design/stage-a-guided-successor.md`.

## Repository state

- Latest prior local milestone: `aegis-360@7234a04` (guided v2b source, exact
  runtime evidence, frozen real-evaluation scripts). The v3 result is a new
  local milestone; resolve its commit with `git log -1` after committing.
- T7 products, model weights, frames and raw model outputs remain outside Git.
- The last published exact-SHA green CI claim is `4b78e1a`. Current local
  commits have no CI result; no Stage A build has been published.

## Verified

- Xcode 27.2 RC and Metal Toolchain 27B47 are installed on T7. An isolated
  SwiftPM target builds offline on T7 with network denied by macOS Seatbelt.
- Pinned MLX Swift LM and vendored xgrammar source provenance, toy grammar
  probe and installed tokenizer gate were checked. xgrammar does not enforce
  conditional abstention; the strict repo validator remains mandatory.
- Guided v3 exact runtime tree SHA-256 is
  `5e8f4a9e92432a552d65b6dfc0eebc77848b24e316fdc221c67e4ca93dc51184`.
- v3 retained synthetic gate passed 37/37 in 210.21 seconds. Synthetic model
  smoke emitted 405 valid JSON bytes, with empty private TMPDIR, numeric MLX
  metrics, nominal thermal and swap rise about 1.90 GB.
- Final v3 real one-packet smoke had retained completion, passing postcheck,
  401 valid bytes, class `no_semantic_change`, nominal thermal and exact known
  macOS warning only on stderr.
- Two serial six-packet runs completed 12/12, repeated output bytes for each
  packet, and matched 3/6 known labels each. Maximum per-invocation sampled
  swap rise was 353,433,027 bytes; maximum sampled RSS 1,164,148,736 bytes;
  maximum MLX peak active 5,139,256,118 bytes. Thermal nominal or fair.

## Rejected and limitations

- The original unconstrained one-packet output was prose. Guided decoding
  repaired format; it did not pass semantic accuracy.
- v2b and early v3 real smokes with postcheck or stderr failure remain
  operational abstentions. Their classes were not counted.
- The guided v3 Stage A candidate is rejected for 3/6 accuracy, despite
  byte-level repeatability. Do not feed its classes to the planner.
- Trivy/Syft did not cover Swift/C++; Semgrep failed at startup. Provenance
  and bounded execution do not prove absence of vulnerabilities.
- A six-packet known-label test does not establish generalization, viewer
  preference, or whether the error is preprocessing, prompt, model or class
  derivation. Sampled RSS is not unified-memory total.

## Pending

## Next commands

Inspect the actual SmolVLM2 image-token and preprocessing path with bounded
model-free probes. Preserve the six packets as diagnostic examples; a changed
treatment requires a fresh independent labelled holdout. Do not rerun the
frozen schedule for tuning. First verify the milestone and current Git state:

```sh
cd ~/Documents/aegis-360
python3 scripts/check_handoff.py
git status --short --branch
```

## External artifacts

The approved external working space is the configured T7 project data root.
Runtime/model/media, private frames and output, metrics, build scratch and
compiled products stay there. The decisive private run status is under
the T7 `build/sga4/` directory. No delegated work or background
job is running.

## Active agents

No delegated work or background job is running.

## Safety and claims

A local build proves a build, 37 synthetic cases prove their retained host
contract, and the 12 real invocations prove only the bounded known-label
result. The candidate has no semantic authority. Git history is the archive;
this handoff describes the latest state.
