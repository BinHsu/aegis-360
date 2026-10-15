# Private synthetic coordinator workplan

Status: parallel local investigation and bounded implementation; no invocation authority

The published baseline is `BinHsu/aegis-360@3eeee16`, whose exact-SHA
`handoff-contract` CI run 38660913858 passed. A local handoff-only checkpoint
follows it. The 33 adapter-owned fixture cases freeze from distinct retained
claims and execute natively in closed order. Four coordinator-owned rows remain
shape placeholders. The protocol authority is
`docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md`, especially
its synthetic coverage and exact case/result contract. Read ADR 0010 and
`docs/design/sparse-story-private-invocation.md` before changing architecture.

All tasks use synthetic local assets only. Keep public authority APIs closed;
do not acquire models/media, push, publish, or edit the shared handoff/status.
An expected enum by case name is not an observation. Distinguish actual native
execution, preflight rejection, cleanup ownership, and exact rebuild evidence.
Preserve unverified or replaced paths; do not remove unfamiliar files. Return a
completion packet with `status`, `files_changed`, `tests_run`, `verified`,
`limitations`, `unresolved`, and `recommended_next_action`.

## Cardinality and rebuild worker

Exclusive writes: `src/aegis360/sparse_story_coordinator_cardinality.py` and
`tests/test_sparse_story_coordinator_cardinality.py`. Determine the exact proof
needed for `single_invocation` and `receipt_rebuild`, and implement a bounded
private helper only if it proves the protocol outcome through the retained
candidate/session, capture and exact bytes. A probe receipt alone is not an
adapter run receipt. Show a negative test that catches duplicate invocation or
a changed rebuild. Report missing prerequisites without fabricating a case PASS.

## Bundle mutation worker

Exclusive writes: `src/aegis360/sparse_story_coordinator_mutation.py` and
`tests/test_sparse_story_coordinator_mutation.py`. Design and, where safe,
implement a private `bundle_mutation` observation using an exactly owned
synthetic selected bundle. Mutation must invalidate retained trust before
spawn; cleanup must not delete a changed or unowned leaf. Show a controlled
mutation that distinguishes actual trust rejection from case-name assignment.

## Replacement race worker

Exclusive writes: `src/aegis360/sparse_story_coordinator_replacement.py` and
`tests/test_sparse_story_coordinator_replacement.py`. Design and, where safe,
implement a private `replacement_race` observation at the publication/cleanup
boundary using exact owned identities. The replacement must survive and must
not be mistaken for an owned peer. Show a negative control that fails if the
cleanup removes the replacement. Do not claim a full receipt or aggregate.

## Integration owner

The main agent owns `src/aegis360/sparse_story_synthetic_plan.py`,
`tests/test_sparse_story_raw_probe_transport.py`, `docs/handoff/current.md`,
and `docs/status.md`. It reviews worker diffs, runs relevant gates, resolves
the common interface, implements the complete 37-row result only after all
four coordinator observations have proven their required lifetime and bytes,
and checks exact-commit CI only after an authorized push.
