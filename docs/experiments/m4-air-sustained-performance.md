# M4 Air sustained performance

Status: Planned

## Question

Can the complete POC iterate and finish reliably on the fanless M4 MacBook Air
with 16 GB unified memory and externally stored models/media?

## Decision unlocked

Identify measured bottlenecks and decide whether VideoToolbox, MPS/Core ML,
Metal, reduced sampling, smaller models or cache changes are justified.

## Workloads

Measure proxy creation, perception, interest/candidate generation, planning,
proxy preview and one final render separately and end-to-end. Use all three
benchmarks; include a long enough continuous workload to expose thermal
behavior. Compare only low-effort acceleration variants available in the
implemented pipeline.

## Procedure and metrics

Record exact Mac/OS, power state, ambient/initial thermal state, external volume
and connection, free space, FFmpeg/model/device placement, input/proxy/output
specifications and commit. Sample wall time, throughput over time (including
early and sustained windows), peak RSS, memory pressure, swap, CPU/GPU/energy,
thermal pressure, cache I/O/size and failures.

## Acceptance criteria

Fix iteration and completion budgets before timed runs. Required invariant:
bounded memory with normal peak RSS below the 10 GB target, no unexplained
sustained swap growth, no data loss if the external volume disappears, and no
throughput collapse that prevents completing the benchmark. An optimization is
adopted only when its implementation cost improves time-to-evidence or is
required to meet these gates.

## Run record

Commands, monitoring method, run order, repetitions, raw artifact locations,
results, variability, limitations and conclusion: TBD. No result has been
observed.
