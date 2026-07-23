# Documentation index

This is the canonical documentation index for agents and contributors. Start
with `AGENTS.md`, then use this page to read only the material relevant to the
task. The repository is currently documenting its decisions; it does not yet
contain an implementation or verified benchmark results.

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

If two authoritative documents disagree, stop, report the conflict, and do
not invent a resolution.

## Reading map by task

| Task | Read first |
| --- | --- |
| Understand current progress | `docs/status.md`, then `docs/adr/README.md` |
| Change product scope or offline behavior | ADR 0001, ADR 0002 |
| Change accepted input formats or validation | ADR 0003 |
| Choose storage, compute, or Apple-specific acceleration | ADR 0004, ADR 0005 |
| Change proxy, caching, or memory behavior | ADR 0005 |
| Change interest scoring, candidate shots, or planning | ADR 0006 |
| Add media or change evaluation | ADR 0007 and `benchmarks/README.md` when present |
| Choose or replace a model backend | ADR 0008 |
| Make a claim about GoPro, Insta360, prior art, or licensing | Relevant material in `docs/research/` when present; do not rely on README prose |
| Report performance or quality | Relevant protocol in `docs/experiments/` when present; include its environment and artifacts |

## Suggested first read for a new agent

1. `AGENTS.md`
2. `docs/status.md`
3. `docs/adr/README.md`
4. The ADRs and design/experiment documents named for the assigned task

Do not read the historical
`docs/archive/aegis-360-scaffold-v2.md` as current authority. It is an input
to the project history and contains decisions superseded by the accepted
ADRs.
