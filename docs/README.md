# Documentation index

This is the canonical documentation index for agents and contributors. Start
with `AGENTS.md`, then use this page to read only the material relevant to the
task. The repository contains evolving implementation and bounded benchmark
evidence; neither should be read as a finished product claim.

## Authority and document roles

When documents conflict, use this order:

1. `AGENTS.md` governs agent workflow, safety, scope, and repository rules.
2. Accepted ADRs in `docs/adr/` govern settled product and architecture
   decisions. A later ADR may explicitly supersede an earlier one.
3. Current documents in `docs/design/` describe an evolving implementation
   design. They must not silently contradict an accepted ADR.
4. Reproducible results in `docs/experiments/` provide evidence. Results can
   motivate a new ADR but do not change a decision by themselves.
5. `docs/research/` records external claims, sources, and inferences; it is
   evidence, not a project decision.
6. `docs/status.md` reports current progress and the next evidence gate.
7. `docs/handoff/current.md` reports the latest operational checkpoint,
   repository delivery state, and exact continuation command.

If two authoritative documents disagree, stop, report the conflict, and do
not invent a resolution.

## Reading map by task

| Task | Read first |
| --- | --- |
| Understand current progress | `docs/status.md`, then `docs/adr/README.md` |
| Resume interrupted or cross-agent work | `docs/handoff/current.md`, then the documents it links |
| Change product scope or offline behavior | ADR 0001, ADR 0002 |
| Change accepted input formats or validation | ADR 0003 |
| Choose storage, compute, or Apple-specific acceleration | ADR 0004, ADR 0005 |
| Change proxy, caching, or memory behavior | ADR 0005 |
| Change interest scoring, candidate shots, or planning | ADR 0006 |
| Change event timeline, semantic review packets, or human-review role | ADR 0010, then ADR 0006 |
| Change event-semantic adapter output or evidence-to-utility mapping | `docs/design/event-semantic-evidence.md`, ADR 0010, then ADR 0006 |
| Change vertical/group composition policy | `docs/design/interest-model.md`, `docs/experiments/vision-face-composition-probe-2026-08-09.md`, then ADR 0006 |
| Change audio/reaction-event evidence | `docs/experiments/apple-sound-reaction-gate-2026-08-15.md`, `docs/design/interest-model.md`, then ADR 0006 |
| Change semantic detection, detector refresh, tracking grace, or lifecycle traces | `docs/design/perception-and-tracking.md`, `docs/experiments/native-detector-refresh-trace-2026-07-29.md` |
| Resume continuous multi-view semantic acquisition | `docs/experiments/yolox-multiview-semantic-events-2026-08-02.md`, then `docs/design/perception-and-tracking.md` |
| Resume semantic-seeded native tracking | `docs/experiments/semantic-seeded-vision-lifecycle-2026-08-06.md`, then `docs/design/perception-and-tracking.md` |
| Change stabilization, motion-character, or segment treatment | `docs/design/spherical-stabilization-and-segment-policy.md`, ADR 0002, ADR 0005, ADR 0006 |
| Add media or change evaluation | ADR 0007 and `benchmarks/README.md` when present |
| Choose or replace a model backend | ADR 0008 |
| Research the next semantic detector after YOLOv3 Tiny | `docs/research/replacement-semantic-detector-2026-07-29.md`, then ADR 0008 and the model manifest |
| Evaluate the proposed local scene-context VLM | `docs/research/local-vlm-candidate-2026-08-11.md`, then `model-manifests/candidates.toml` |
| Validate converted detector numerical equivalence | `docs/experiments/yolox-tiny-conversion-equivalence-protocol.md`, `scripts/compare_detector_equivalence.py` |
| Locate or verify external model weights | `model-manifests/README.md`, then `model-manifests/manifest.toml` |
| Inspect proposed, not-yet-acquired model assets | `model-manifests/candidates.toml`; never pass it to the installed-asset verifier |
| Make a claim about GoPro, Insta360, prior art, or licensing | Relevant material in `docs/research/` when present; do not rely on README prose |
| Report performance or quality | Relevant protocol in `docs/experiments/` when present; include its environment and artifacts |

## Suggested first read for a new agent

1. `AGENTS.md`
2. `docs/handoff/current.md`
3. `docs/status.md`
4. `docs/adr/README.md`
5. The ADRs and design/experiment documents named for the assigned task

Do not read the historical
`docs/archive/aegis-360-scaffold-v2.md` as current authority. It is an input
to the project history and contains decisions superseded by the accepted
ADRs.
