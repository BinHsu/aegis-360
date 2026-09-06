# Structural chapter blind replication v1

Status: selection proof frozen; no new score or pixel

Selection-policy SHA-256:
`c4a1f411e26de8061c46f49e7db43474b4aeb75839d7d7f140cc38bd5df2e6cb`.

Selection-proof SHA-256:
`ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567`.

## Claim boundary and staged lineage

This is a fresh-reviewer, label-blind, within-source replication. It is not
sample-, pixel- or source-independent: earlier development packets exposed up
to ±15 seconds of context. The immutable sequence is:

1. source/timeline plus committed selection policy;
2. exact 26-entry universe and selection-proof artifact;
3. proof-bound private schedule and salted neutral public index;
4. sanitized transient bundle and two frozen independent reviews;
5. mapping reveal, label-free structural scores, then joined evaluation.

No later hash feeds an earlier stage. No replacement sample or retuning is
allowed after a stage is frozen.

## Selection policy

The universe is every one of the 26 exact scene signals in timeline
`f850a8a5…a7ee1`. The proof builder exact-rebuilds each legacy proof packet from
that timeline and context grid `26b869dd…fbf1f`, using its frozen ±15, ±3 and
±0.25-second six-anchor policy. These proof packets are lineage inputs only;
they are distinct from later neutral review packets at ±3.75/±2.25/±0.25.
The proof records packet hash, event ID, signal ID and rational source time, and
recomputes every disposition. Development exclusion is absolute center distance
strictly less than eight seconds from 53, 84.6, 163.5, 168.4 or 222 seconds.

Eligible rows use SHA-256 over the exact UTF-8, no-newline, lowercase preimage
`source_sha256|timeline_sha256|structural-blind-replication-v1|event_id|signal_id`.
Require globally unique signal IDs and event/signal pairs. Scan digest ascending
with event-ID then signal-ID ascending tie break. Select a row only when
its distance from every earlier selection is at least eight seconds. Stop at
eight; fail if the cap cannot be filled. Record excluded, separation-rejected,
selected and after-cap rows in digest order. Never backfill.

The one frozen build accounts for all 26 rows: eight selected, nine development
excluded, four rejected for minimum separation and five after cap. Selection
rank order is event/signal `0023/0024` at 205.6 s, `0003/0004` at 35.1 s,
`0002/0002` at 24.5 s, `0009/0010` at 95.6 s, `0014/0015` at 121.6 s,
`0021/0022` at 193.4 s, `0016/0017` at 132.4 s and `0004/0005` at 43.1 s.
The artifact contains no pixels, audio, labels or local paths and grants no
semantic, boundary, camera or render authority.

## Label-free scoring contract

Only acquisition, descriptor, sample offsets and score equation are extracted
from labeled config `8baf66a0…f7f7a2`. Canonical compact sorted-key JSON with
ASCII escaping and no newline has subset SHA
`7f8b05656986030715f226f9c9c33fc375e1afe3e361fc37b54651851a8aa5cd`.
The replication scorer accepts only proof-selected rational timestamps, source
and this subset; it has no expected class or semantic-evidence input.

Review media uses separate offsets ±3.75, ±2.25 and ±0.25 seconds. These six
composites never enter the eight-frame score calculation.

## Gates reserved for the proof-bound schedule

Before any image, a later schedule config must freeze file-only 256-bit salt
handling, HMAC packet/order IDs, exact public projection, PNG metadata stripping
and atomic no-overwrite publication. Public data may expose only neutral row
roles, anonymous view slots and safe relative refs—not time, IDs, score, digest,
direction, selection rank or development proximity.

Two fresh reviewers work independently. Only unanimous `story_change` and
unanimous `no_semantic_change` packets enter ranking; at least two of each are
required. `min(story score) > max(no-change score)` passes. Adequate balance
with failed ordering rejects; disagreement, artifact, abstention or class
imbalance is inconclusive. Neither case triggers backfill. A pass remains
within-source evidence and grants no boundary, threshold, camera or render.

An independent no-artifact audit passed the final universe reconstruction,
legacy packet contract, exclusion/separation rules, total order, label-free
descriptor subset and staged authority boundary.
