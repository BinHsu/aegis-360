# Shot planner

Status: Active design; formulation and weights require experiment

## Inputs and output

The planner consumes timestamped candidate shots and explainable utilities. It
emits a chronological path of yaw, pitch, FOV, subject/context identity,
continuous transitions and explicit cuts. It does not decode media or infer
objects.

## Baselines and main approach

- Fixed-forward is the minimum baseline.
- Greedy utility plus hysteresis/minimum dwell is the behavioral baseline.
- The main POC uses global dynamic programming, Viterbi, or an equivalent DAG
  search over bounded candidates.

Per-frame argmax is not a production director.

## Objective terms

Reward candidate interest and coverage. Penalize angular displacement,
velocity/acceleration/jerk, unnecessary cuts, subject switching, repetition,
poor composition and missed important events. Enforce minimum dwell or model
its violation as a prohibitive cost. Continuous pan and hard cut are distinct
transitions.

All terms must be individually recorded. Weights live in versioned config,
not source code. Plans are generated from cached analysis, enabling rapid
weight iteration with proxy previews.

## First-slice greedy configuration

The initial executable contract is
`config/greedy-first-slice-v1.toml`, with schema
`aegis360.greedy-config.v1`. It requires exactly four editorial weights:
`presence`, `persistence`, `composition`, and `forward_prior`. Detector
confidence is adapter/perception evidence and must not be added as an
editorial weight. The loader fails closed on missing fields, unknown fields,
unsupported schema versions, and non-finite or out-of-range numbers.

The same file persists minimum dwell, switch margin, challenger hold, and
`camera.min_angular_change_degrees`. The camera value only decides whether a
camera change is large enough to retain as a sparse keyframe. It is a tunable
POC threshold, not evidence of perceptual comfort and not a maximum angular
speed. Traces retain the validated values and schema version so runs can be
reproduced.

## Continuous-transition constraint

The current renderer path uses independent quintic smootherstep segments.
Each segment is rest-to-rest: coordinate velocity and acceleration are zero
at both endpoints, so a multi-segment yaw/pitch/FOV path is C2 at an interior
keyframe. It is not generally C3. The one-sided coordinate jerk is
`60 * delta / duration^3`; unequal adjacent displacement or duration therefore
creates a finite jerk jump even though velocity and acceleration are
continuous.

`keyframe_continuity` records the exact one-sided yaw, pitch and horizontal-FOV
derivatives after seam-aware yaw unwrapping. These are coordinate-angular
metrics, not a perceptual comfort model or a full orientation-space metric.
No comfort threshold has been selected. Candidate-transition generation must
expose these measurements before the planner can claim a comfortable path;
a coupled spline or optimizer remains a later option if benchmark evidence
shows the rest-to-rest joins are inadequate.

## Hypotheses

- A bounded candidate graph permits whole-video optimization within modest
  memory.
- Global planning reduces reversals and short-lived switches without losing
  event coverage.
- One generic weight set can outperform baselines across the three POC videos.

## Sparse event DP v1

`aegis360.global-event-plan.v1` is the first global-planner slice under ADR
0010. It consumes ordered, nonoverlapping Event Review Packets paired with
checksummed Event Candidate Utility artifacts. Each event offers current and,
when semantic evidence and duration permit, proposed. The versioned policy
sets minimum utility advantage, minimum proposed dwell, two-way fixed switch
cost, grid-derived angular cost and repeated-proposed cost.

Dynamic programming optimizes the complete event sequence and records selected
utility plus each planning-cost component per event. A proposed event is
modeled as a bounded cut away and return, so fixed and spherical angular costs
are charged each way. Abstention or a short event exposes current only.
Deterministic candidate-ID ordering breaks ties.

This is genuinely cross-event for repetition but not yet a complete camera
path optimizer: continuous transitions between events and
inter-event non-event utility are not modeled. The limitation is explicit in
the plan and must be closed before claiming the production global planner.

## Acceptance criteria

Compare fixed, greedy and global plans using identical candidates. Report
event coverage, switch/cut counts, short shots, reversals, angular derivatives,
repetition and blind pairwise viewer preference. The global plan must not be
accepted merely because its numerical objective is higher.
