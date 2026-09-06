# Structural chapter blind replication v1

Status: executed and rejected by the frozen strict-ordering gate

Selection-policy SHA-256:
`c4a1f411e26de8061c46f49e7db43474b4aeb75839d7d7f140cc38bd5df2e6cb`.

Selection-proof SHA-256:
`ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567`.

Anonymous-schedule config SHA-256:
`3964162f0cb99bf9959cee1b19bef9fd041a04a76dfae9085052c9babb30d8ba`.

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

The frozen schedule now does so for exactly eight packets and six chronological
rows at ±3.75, ±2.25 and ±0.25 seconds. Reviewer artifacts use opaque slots,
closed observations and bind only the public-index, bundle-tree and schedule-
config hashes. Reviewers receive an isolated sanitized bundle with no repository,
network, conversation history or peer result. The reproducibility mapping above
therefore stays coordinator-side; any reviewer access to it invalidates the run.

The one exact schedule build produced private schedule SHA
`e5e8d27d443829181b1cf61dd04d492f973d9a81043f9ac023ef4addc2dd924f`
and public-index SHA
`f107cfb50956fcaf745ea4d003fbc3b7deab0fac4f184806f67f92d0c913bf59`.
The one exact renderer run produced all 48 sanitized 960x540 RGB PNGs. Its
canonical closed-tree SHA is
`4f55b456dc6d6fa9df58a7f9806b1656ce46934f50bc4e8e045db8b6d4b3c000`;
an independent mechanical pass confirmed exact refs, dimensions, metadata-free
chunks, index byte identity, no symlinks and no extras.

Two fresh isolated reviewers each inspected all 48 images before either result
was opened or any structural score was acquired. Frozen review artifact SHAs are
`71998fe544b413d38c4c93dbc947afe292bc6ef7889a8ace3b98941408fe7930` and
`37a87a207de81e4641392aa1717f39806c4361b5a96d0de0eb07108ac0648eed`.
Both closed schemas exact-validate with eight ordered responses and distinct
opaque slots. The coordinator-private, identity-free distinct-principal
attestation SHA is
`0efe10192a4441f75910932992f2a8c0c0613f4fcade078860d575428cae4bd6`.
Review classifications remained unopened until the already frozen label-free
score adapter was implemented, tested and its real artifact hash frozen.

## Result

The label-free score artifact SHA is
`0c0c059ba1d1dc5b9498dc173d40cefcd261f8208c1c17f0923e72ef83d2e81b`.
Only after it and both review hashes were frozen did the raw-byte coordinator
join them. Evaluation artifact SHA is
`7c9b4ae8b5d3697b6c44ed7fd0e98f95863b056e19d7d9044c6f51f4bf440afb`.

Both reviewers agree on all eight packets: six `story_change` and two
`no_semantic_change`. Class balance is adequate, but the lowest story score is
0.04363508 at 205.6 seconds while the highest no-change score is 0.06806761 at
132.4 seconds. The predeclared result is therefore `reject`, not `inconclusive`.

| Source second | Event | Unanimous class | Score |
| ---: | --- | --- | ---: |
| 24.5 | `event:multi:0002` | no semantic change | 0.02073898 |
| 35.1 | `event:multi:0003` | story change | 0.07047933 |
| 43.1 | `event:multi:0004` | story change | 0.06766957 |
| 95.6 | `event:multi:0009` | story change | 0.17297827 |
| 121.6 | `event:multi:0014` | story change | 0.13457435 |
| 132.4 | `event:multi:0016` | no semantic change | 0.06806761 |
| 193.4 | `event:multi:0021` | story change | 0.10136846 |
| 205.6 | `event:multi:0023` | story change | 0.04363508 |

Post-reveal visual diagnosis explains the inversion without changing it. The
205.6-second story change moves from a confined forest path to a suspension-
bridge/river context, yet both sides retain dense grayscale edges and vertical
structure after coarse cyclic alignment. The 132.4-second no-change packet stays
within one mountain-trail activity, while viewpoint rotation, a nearby hiker and
foreground/background redistribution produce a larger tile-structure distance.
The descriptor is sensitive to viewpoint and spatial rearrangement but not
monotonic with story change. Do not tune a threshold, discard either packet,
backfill, or promote this score to chapter authority.

After evaluation, both transient bundle copies, temporary reviewer responses
and diagnostic montages were deleted as predeclared. Coordinator metadata,
reviews, scores, evaluation, source, schedule and owner-only salt remain. The
48 PNGs are not directly recoverable, but the frozen inputs can re-render a
bundle whose canonical tree must equal `4f55b456…3c000`.

Two fresh reviewers work independently. Only unanimous `story_change` and
unanimous `no_semantic_change` packets enter ranking; at least two of each are
required. `min(story score) > max(no-change score)` passes. Adequate balance
with failed ordering rejects; disagreement, artifact, abstention or class
imbalance is inconclusive. Neither case triggers backfill. A pass remains
within-source evidence and grants no boundary, threshold, camera or render.

An independent no-artifact audit passed the final universe reconstruction,
legacy packet contract, exclusion/separation rules, total order, label-free
descriptor subset and staged authority boundary.
