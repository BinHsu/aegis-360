# 0008: Keep model backends behind task adapters

Status: Accepted

## Context

The fastest useful detector, tracker, scorer, or active-speaker model may
change as accuracy, Apple-hardware compatibility, memory use, implementation
time, and licensing are measured. Treating one model vendor as the product
would make experiments and license review harder.

## Decision

Define task-level adapters for detector, tracker, scorer, and any later
active-speaker component. Ultralytics may be used as an initial POC backend,
but it is replaceable and is not part of aegis-360's identity. Adapter
contracts should expose normalized evidence needed by downstream spherical
geometry and planning rather than leaking vendor-specific objects.

Adapters are for rapid model substitution within the POC, not for providing
cross-platform parity.

## Consequences

- Model implementation, weights, training data, and runtime licenses must be
  reviewed independently from the repository's intended Apache-2.0 license.
- AGPL or otherwise restrictive dependencies must remain isolated, and their
  distribution implications cannot be dismissed because this is a POC.
- Do not build unnecessary abstraction layers beyond the task contracts needed
  to compare backends.
- Backend selection and acceleration are empirical design choices governed by
  ADR 0004 and future experiments.
