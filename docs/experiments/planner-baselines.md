# Planner baselines

Status: Planned

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
result has been observed.
