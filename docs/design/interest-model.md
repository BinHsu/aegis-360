# Interest model

Status: Active design; signal weights are hypotheses

## Editorial objective

Approximate what an ordinary first-time viewer would want to see while
preserving context and avoiding uncomfortable camera behavior. A viewing
candidate may be a person/object track, a group or interaction region, the
forward direction, or an environmental/context view.

## Initial explainable evidence

- person/object presence and confidence;
- track persistence and visibility;
- motion or action change, not raw motion magnitude alone;
- forward-motion prior for first-person travel footage;
- scene novelty and repetition;
- composition/viewport fit;
- continuity with the incumbent subject or context.

Each signal has a name, raw value, normalization method, weight and provenance
in the decision trace. Missing evidence is explicit. Motion must not dominate
quiet but meaningful subjects, and high background flow must not automatically
become the subject.

## Candidate generation

Generate a small, bounded set per decision interval: persistent subject views,
useful group views, forward/context view, and an incumbent continuation. Merge
near-identical spherical directions. Candidate intervals may begin at regular
analysis timestamps or detected events; the choice is tested rather than
assumed.

## Deferred signals

Active speaker, gaze, detailed action recognition, face identity,
personalization and trained end-to-end ranking are deferred unless benchmark
failures demonstrate their necessity.

## Acceptance criteria

- Every chosen view can be explained from stored evidence and planner costs.
- Signal ablations expose whether forward, motion or detector confidence is
  dominating unexpectedly.
- Candidate generation includes acceptable directions for manually reviewed
  important events in the benchmark excerpts.
- Scores are deterministic for fixed inputs, models and configuration within
  documented backend limits.
