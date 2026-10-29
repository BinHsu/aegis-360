# Stage A validation assessment — 2026-10-30

The original unconstrained SmolVLM2 packet failed the closed-output gate by
returning prose. The pinned guided decoder was built offline, checked against
the frozen tokenizer and schema, then passed an exact-runtime 37-case retained
isolation suite and synthetic model format smoke. After correcting the metrics
sidecar location and isolating one exact macOS sandbox warning, the revised
candidate completed a real operational smoke and two serial runs over six
predeclared real packets. The original diagnostic output was never counted.

| Claim | Measured evidence | Assessment |
|---|---|---|
| Closed format | 12/12 real invocations returned strict-validator-accepted JSON | Benefit confirmed for format |
| Repeatability | 6/6 corresponding raw output pairs were byte-identical | Benefit confirmed for this bounded schedule |
| Known-label semantics | 3/6 correct in each run; two story changes and one no-change miscalled capture artifacts | Candidate rejected |
| Resource behavior | Per-invocation sampled swap rise at most 353,433,027 B; sampled RSS at most 1,164,148,736 B; MLX peak active at most 5,139,256,118 B; nominal/fair thermal | Bounded feasibility only |
| Privacy/isolation | 37/37 retained synthetic cases and real postcheck passed; exact known 137-byte macOS warning exception | Operational gate passed under revised candidate contract |

The benefit is **real but insufficient**: guided generation solves the
observed output-format problem and produces repeatable output, while the
current Stage A semantic classes cannot be used as planner evidence. This
result does not establish that SmolVLM2 itself is unsuitable. The error may
arise from image preprocessing, temporal representation, prompt, model
capacity, or class derivation. The six labelled packets have served as
diagnostics and cannot be treated as an unseen final holdout after tuning.
Next inspect the actual image-token and preprocessing path with model-free
probes, then define a new independent labelled holdout for any changed
treatment. Full evidence is in
`stage-a-guided-v3-known-label-2026-10-30.md`.
