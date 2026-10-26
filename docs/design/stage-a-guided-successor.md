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

## Decision

The supply-chain-audit procedure explicitly stops adoption of a repository
whose history starts as a single complete commit. This source tree meets that
stop signal. Therefore no new guided target is built or executed for this
investigation, and no model-free grammar proof is claimed. Existing scratch
build files are not proof of an audited or working guided library. The
frozen Stage A protocol still has no valid semantic packet; the failed
SmolVLM2 candidate remains held.

To continue this route, first obtain a source artifact with inspectable
development provenance and verify the exact vendored xgrammar tree against
the identified upstream release, then repeat target-covering supply-chain
review in an isolated environment. That would be a new acquisition and any
subsequent packet/model invocation would require a new bounded diagnostic
protocol. An alternative locally authored constrained decoder could avoid
this dependency, but its design and model interaction are untested.
