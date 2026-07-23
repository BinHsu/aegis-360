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

## Hypotheses

- A bounded candidate graph permits whole-video optimization within modest
  memory.
- Global planning reduces reversals and short-lived switches without losing
  event coverage.
- One generic weight set can outperform baselines across the three POC videos.

## Acceptance criteria

Compare fixed, greedy and global plans using identical candidates. Report
event coverage, switch/cut counts, short shots, reversals, angular derivatives,
repetition and blind pairwise viewer preference. The global plan must not be
accepted merely because its numerical objective is higher.
