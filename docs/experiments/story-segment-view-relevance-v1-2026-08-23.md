# Story segments and candidate-view relevance v1

Status: Executed on 2026-08-23

## Question

Can candidate-view relevance be reviewed without mixing content from opposite
sides of a story boundary? A pass establishes segment-scoped evidence for a
bounded planner experiment. It does not establish full-video coverage or let a
reviewer select the rendered view.

## Boundary correction

Exact six-anchor story contact sheets showed that before/after sides of one
event often require different directions. Far context can also cross later
cuts: the 84.6-second packet reaches the 95.6/99.8 sequence, while the
163.5-second packet reaches the waterfall chapter. One event-wide candidate
label would therefore conflate distinct shots.

`aegis360.story-segment-timeline.v1` partitions the full source window at every
retained scene timestamp and preserves each segment's left/right event and
signal lineage. Old Ghost Road has 26 boundaries and 27 positive-duration
segments, with durations from 1.4 to 25.1 seconds. The external timeline SHA is
`c54aaafe55e17126c4004bd9b5c949eca6ab17a216d71e640c7f5bc8edc3967e`.
High-recall evidence may over-segment; the artifact does not declare chapters,
importance or views.

## Segment packet and runner

`aegis360.story-segment-review-packet.v1` samples 20%, 50% and 80% strictly
inside one segment. Each sample is one temporary four-cardinal 2x2 composite,
so the adapter receives three images/12 source viewports. Even the 1.4-second
fixture samples remain within their segment. A real segment 0010 run passes
3/3 768x432 probes and runner cleanup.

Five representative external packet SHA-256 values are:

- 0007: `115f1c51765f0898ee25e5811ce56af9d864ee70656607db84609107e4e2ec6d`;
- 0010: `a39b975e14735d2b2aa6ab9039e03d84df8c707fe370cbf81ef57a7c7bb23387`;
- 0020: `e6fa8bdb91bd9b0862cd0fe9a1fda4413380545331381daaa006409f92ab9bd4`;
- 0021: `936b31cb93ce4a88cdb5fb127ac1c011322e98a0cbef775cab31e7667ddc79d6`;
- 0026: `baf6af7821eb147878032bbc3ea85d037b17f082e702559d6ac2add2a76a1e89`.

## Closed relevance and audit

Observed `aegis360.segment-view-relevance.v1` covers all four candidates in
grid order with visibility, segment relevance and temporal consistency. It
requires exactly one primary. Abstention carries no candidate claims. Neither
mode selects a view or applies transition costs.

Agent review of the exact three-sample composites labels 0007 cardinal 1,
0010 cardinal 0 and 0021 cardinal 1 as stable primaries. Segment 0020 changes
too much to justify one primary; segment 0026 is a repeated closing logo that
should hold the prior view. Both abstain. These are agent benchmark labels, not
owner ground truth. Temporary audit pixels were deleted.

Bound relevance SHA-256 values are:

- 0007: `f336e218f03c582aacc98894061b54a81f9198e371a7d20bc8c934f6f5c6eefb`;
- 0010: `32f754994cbe29805c0cb577419106253df547dfe7fdb95f45668c25c080b918`;
- 0020: `e6a8ba06225cb4414286c893d16b9a24893401d1bbc69de067080f2712a30836`;
- 0021: `52bdb56892e2317b33ac7d67a16cbca2f8e451af4b518bafc64622dbd6c3efde`;
- 0026: `655202b5b6d4a0579c5c2df102cad1513faa0837360c3019372d2c521a8edd06`.

## Conclusion and next gate

Candidate relevance belongs to shot segments, while story semantics belongs to
boundaries. Five labels do not cover all 27 segments, so a full-film plan would
be unsupported. The next gate is a bounded planner over 53–95.6 and
163.5–174.4 seconds: unreviewed/abstained segments retain the current view;
observed relevance may propose a change subject to boundary constraints.
