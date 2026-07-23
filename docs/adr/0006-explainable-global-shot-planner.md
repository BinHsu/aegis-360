# 0006: Plan shots globally from explainable evidence

Status: Accepted

## Context

Per-frame maximum saliency produces jitter, rapid subject changes, and choices
that ignore narrative continuity. Detection and tracking say what exists, not
what an ordinary viewer should watch. Offline processing allows decisions to
use future context.

## Decision

Generate candidate views over time and score them with inspectable evidence.
Initial evidence may include person/object presence, track persistence, motion
change, travel-direction prior, scene novelty, interaction/context, and
composition. Plan across the recording with a global DP, DAG, Viterbi-style,
or equivalent optimization that balances content utility against camera
motion, acceleration/jerk, cuts, subject switches, repetition, and minimum
dwell constraints.

Implement fixed-forward and greedy-with-hysteresis directors as baselines.
Per-frame argmax is not the main director. Emit a machine-readable decision
trace explaining candidates, evidence, costs, and selected paths.

## Consequences

- Subject handoff is a core planning capability, not a deferred product detail.
- Exact signals, weights, graph representation, and solver remain design and
  experiment questions rather than fixed by this ADR.
- Smoothing alone cannot substitute for editorial planning.
- The offline planner can reconsider early choices using later evidence.
