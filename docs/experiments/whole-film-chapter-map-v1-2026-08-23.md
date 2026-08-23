# Whole-film chapter-map contract v1

## Question

Can the planner prove that every retained scene boundary has been considered
before any future-chapter foreshadow is even eligible for selection?

## Result

`aegis360.whole-film-chapter-map.v1` now binds one exact story-segment timeline
and one checksummed closed config. Every retained boundary must appear exactly
once and in timeline order with its `event_id`, `signal_id`, timestamp and
structural disposition. Missing, duplicated, reordered, invented or ambiguous
entries fail construction.

This signal-level key is necessary because one fused event can contain more
than one scene-change signal. Existing event-scoped story labels cannot safely
select which of those timestamps starts a chapter.

The builder deterministically groups the complete ordered segment partition
into gap-free chapters. Chapter roles use a closed enum and reviewer provenance
is explicit; a local model requires an exact asset SHA-256. The artifact is
candidate-free and emits no geometry, teaser interval or renderer command.
Most importantly, it declares temporal reordering unauthorized.

The committed fixture covers one within-chapter cut and one exact chapter
boundary, producing a journey chapter followed by a destination chapter. Four
tests cover exact derivation, missing/reordered/unknown boundary failure,
signal/timestamp mutation, aligned chapter roles and reviewer provenance.

## Interpretation

This passes the mechanical completeness layer of ADR 0011. It does not prove
that the declared chapters match an ordinary viewer's understanding. A
separate authorization gate must require validated chapter-map evidence and
then independently verify any proposed prefix/payoff interval. Current Old
Ghost Road evidence is incomplete and cannot be promoted into a full map.

That structural eligibility gate is now executable. It validates the exact map
derivation, binds an independent qualification and fixed policy, requires two
or more chapters plus a later `destination`, and returns closed reason codes
for abstention or missing destination. Its authority stops at allowing one
future planner invocation; no teaser interval or render is selected. Three
tests cover pass, abstain, absent destination, stale qualification and policy
mutation.

The owner reviewed the unchanged original stream with eight chapter markers
and accepted the structure as natural. A new owner-qualified lineage preserves
the earlier coarse abstention artifact rather than overwriting it. The exact
eligibility gate now returns true with no reasons, while still selecting no
teaser interval or view. This is source-specific validation, not evidence that
an automatic chapter model generalizes.
