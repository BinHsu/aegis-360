# Planner baselines

Status: In progress — fixed-forward renderer and dependency-free greedy baseline exist; comparative evaluation remains planned

## Question

Does explainable global planning produce a more watchable Full Story than
fixed-forward and greedy utility with hysteresis?

## Decision unlocked

Validate or reject the POC's core auto-director hypothesis and select an
initial planner formulation/configuration.

## Inputs and controls

Use one cached candidate/evidence set per benchmark for all planners. Compare:
fixed-forward; greedy with minimum dwell/hysteresis; global DP/Viterbi/DAG.
Generate identically encoded proxy previews and randomize/blind their labels.

## Metrics

Reviewed-event coverage, missed events, cuts, switches, short shots, reversals,
angular velocity/acceleration/jerk, repetition, objective-term breakdown,
planner wall time/memory, and blind pairwise preference with recorded viewer
count and protocol.

## Acceptance criteria

Before viewing results, define material preference/coverage thresholds and
non-regression limits for discomfort metrics. The global planner advances only
if it improves viewer preference or event coverage over both baselines without
unacceptable motion, missed events or complexity. A higher internal score is
not sufficient.

## Run record

Commit, candidate cache IDs, config hashes, preview hashes, annotation/viewer
protocol, results, statistical limitations, artifacts and conclusion: TBD. No
comparative result has been observed. The fixed-forward smoke run is recorded
in [fixed-forward-baseline.md](fixed-forward-baseline.md); it makes no quality
claim.

### Greedy baseline implementation check (2026-07-23)

The executable baseline consumes timestamped, precomputed candidate evidence
and emits deterministic JSON-compatible decisions with named score components,
transition distance, selection reasons and fallback warnings. It applies three
separate guards: minimum dwell, a utility switch margin, and a sustained-best
challenger hold interval. Dependency-free unit fixtures verified that a
transient challenger does not cause a switch, a sustained superior challenger
does, ties resolve by ascending candidate ID, a missing incumbent falls back,
and a +179° to -179° transition records a 2° spherical distance. This is an
implementation behavior check only; no benchmark-quality comparison has run.
