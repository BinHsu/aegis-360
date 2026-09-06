# Skiing gradual-chapter blind protocol

Status: Frozen protocol; not yet executed

## Question

Can a low-cost, full-source proposal signal recover gradual activity or context
changes in the 616.392-second Skiing benchmark without learning the owner's
answer, promoting motion artifacts, or requiring per-frame semantic inference?
A proposal is review scope only. It grants no story boundary, candidate-view,
timeline, planning, temporal-reordering, or rendering authority.

## Frozen separation

Before anyone observes proposed timestamps or review pixels, freeze and hash:

- the proposal algorithm, implementation revision and complete configuration;
- the maximum proposal count, separation/diversity rules and ordering rule;
- the deterministic negative-control pool and selection procedure;
- this protocol, the closed reviewer form and all acceptance criteria;
- a separate scoring key containing only the ordered coarse progression
  `lift/transport -> own skiing/terrain -> other skiers` and the statement that
  its exact transition times are unknown.

The scoring key is not an algorithm input and is not shown to proposal or review
agents. It must not acquire exact timestamps after proposals are observed.
Skiing is evaluation evidence, not threshold-training evidence. Any tuning after
the key or results are opened creates a new policy version and requires a
different held-out source before making an accuracy claim.

## Proposal and control set

Run the frozen cheap-signal proposal stage once over the complete source proxy.
Retain at most six primary proposals using the frozen selection rule. Selection
must preserve signal-family diversity and temporal coverage rather than merely
taking several adjacent high scores.

Proposal evidence compares complete half-open persistent-state windows
`[t-30,t-10)` and `[t+10,t+30)`. Both windows must meet the sample coverage
required by the separately checksummed implementation policy. A timestamp with
an incomplete outer window is ineligible as a primary proposal; it is not
clamped or scored from asymmetric evidence. This protocol deliberately does not
invent the numeric feature weights, dispersion penalty or threshold: those
belong in the frozen implementation configuration and must be fixed before the
Skiing feature values are inspected.

Precommit controls with this deterministic procedure:

1. Form a 10-second lattice at 30, 40, ... 580 seconds, so every control can
   supply both complete outer review windows.
2. Order the lattice by ascending SHA-256 of the UTF-8 string
   `source_sha256|proposal_policy_sha256|protocol_sha256|control-v1|timestamp`,
   breaking an otherwise impossible digest tie by ascending timestamp. Decimal
   timestamps use one digit after the point.
3. After the frozen proposal list exists, scan that ordered pool and retain the
   first timestamp at least 45 seconds from every proposal, at least 45 seconds
   from each earlier retained control and at least 30 seconds from each prior
   hard-negative timestamp.
4. Stop after three controls. If the pool cannot supply three, record protocol
   insufficiency and do not reduce a separation or substitute a timestamp based
   on signal values, pixels or the hidden key.

The procedure and ordered pool are frozen before proposal observation; actual
control timestamps are resolved afterward only because proposal separation
cannot otherwise be guaranteed. Controls are unlabeled probes, not assumed
negative truth. An independently supported story change at a control exposes a
missed proposal or unmatched extra boundary; it is not called reviewer error.

Mix the proposals with the three controls and give all packets neutral,
deterministically shuffled IDs. The reviewer must not know which are proposals
or controls.

The previous full-source motion onsets are hard negatives at 76.75, 327.25,
386.5, 429.75, 499.75, 506.25 and 565.25 seconds. In particular, 386.5 is not a
validated chapter boundary, 327.25 is stitch/stretch evidence, and 506.25 is
foreground sign parallax. Overlap with a new proposal does not erase this prior
negative evidence; promotion requires genuinely independent persistent
before/after evidence and still fails the protocol's no-hard-negative rule.

## Review packet

Each neutral packet contains exactly six silent four-cardinal composites at
relative offsets `-30`, `-10`, `-2`, `+2`, `+10` and `+30` seconds. Rows remain
chronological. Each composite uses the same declared candidate order and
geometry. A source-edge sample that cannot exist is explicit missing evidence;
it is never clamped, duplicated or invented.

The transient review boundary may expose only neutral packet ID, chronological
row role and declared candidate IDs. Reviewer agents receive those packets in a
fresh context with no repository, conversation history, scoring key or prior
review access. The packet must not expose source title, absolute timestamp,
signal family, score, proposal/control status, expected chapter count, owner
progression, the former 390-second pilot split, or prior reviewer answers.
Pixels are deleted after the adapter finishes.

## Independent review

Two reviewers inspect every packet independently before either answer is
shared. They use the existing closed vocabulary: `story_change`,
`capture_artifact`, `no_semantic_change`, or `abstain`. A story change also
requires complete structural-role, change-type, narrative-function and
viewer-value labels. Other outcomes retain `unknown` for all four labels.

Ask only these non-leading questions before recording the closed result:

1. What visibly persists across the early rows?
2. What visibly persists across the late rows?
3. What, if anything, changes between those two sustained states?
4. Is the difference an activity/context change, ordinary continuous movement,
   a near-object or projection effect, or not distinguishable from this packet?
5. Is the evidence sufficient to make a closed observation without identity,
   intent, causality or speech claims?

Do not mention lift, skiing, other skiers, chapter, boundary, expected answer or
the triggering signal in the questions. Reviewer disagreement or insufficient
context resolves to `abstain`; it is not adjudicated into a positive boundary.

## Acceptance criteria

Open the hidden scoring key only after both review sets and artifact hashes are
frozen. This experiment passes only if all of the following hold:

- at least two ordered, independently observed story boundaries form three
  positive-duration, gap-free chapters;
- the three post-hoc chapter roles follow the hidden coarse progression while
  no exact transition timestamp was supplied by the key;
- every promoted boundary has persistent early-state evidence at both `-30`
  and `-10` seconds and persistent late-state evidence at both `+10` and `+30`
  seconds; a difference confined to `-2/+2` is insufficient;
- both reviewers independently classify every promoted boundary as
  `story_change` with complete compatible labels;
- both reviews agree on the same frozen candidate interval; this is reviewer
  agreement, not ground-truth localization accuracy, because the hidden key
  deliberately contains no exact transition timestamps;
- no more than one unmatched extra story boundary is emitted;
- none of the seven prior motion-onset hard negatives is promoted;
- at least two of the three deterministic controls are rejected as
  `no_semantic_change` or `capture_artifact` and none becomes an unmatched
  promoted boundary;
- the resulting chapters cover the complete source without gaps or overlap;
- any chapter longer than approximately 90 seconds, or with more than 30
  seconds between relevant evidence samples, receives denser fixed-schedule
  review or its segment relevance abstains before production planning.

Authorization by a semantic reviewer remains evidence for the deterministic
typed-boundary adapter; the proposal itself never becomes a boundary. A pass is
evidence for this benchmark and frozen policy, not general accuracy.

Proposal coverage and segment-evidence coverage are separate gates. Six sparse
boundary proposals cannot establish a 30-second evidence cadence over the whole
source. After accepted boundaries form chapters, a separately frozen denser
schedule must cover each derived segment before segment relevance can be marked
observed. Boundary success alone never satisfies that later coverage gate.

## Rejection and fail-closed outcomes

Reject the proposal signal as a sole chapter source if it recovers fewer than
two supported ordered boundaries, reverses the hidden progression, promotes a
hard negative, relies on a momentary frame difference, or exceeds the extra-
boundary limit. Edge-truncated, contradictory or under-sampled packets abstain.
Do not lower thresholds, move controls, reinterpret 386.5 or reuse the owner key
to manufacture a pass.

If boundaries pass but a derived segment violates the evidence-gap rule, retain
the boundary result but withhold observed segment relevance and production
eligibility until the predeclared denser review completes.

## Review burden and owner boundary

The primary gate is capped at nine packets: six proposals plus three controls.
At six composites each, that is at most 54 contact sheets or 216 cardinal
viewport panels per reviewer. Reviewers should stop and record operational
failure if this cannot be completed independently without rushing.

The owner supplies no per-packet label and is not a product-time dependency.
Owner review begins only after automatic evidence, independent review,
mechanical validation and agent pre-review produce a materially different
candidate/baseline render pair that answers a specific directing question. At
that point the owner receives at most two clips, not the proposal packets or
hidden key.

## Required record

An executed result records every frozen hash, proposal/control accounting,
randomized presentation order, missing edge samples, both independent closed
responses, disagreements/abstentions, key-opening time, boundary matching,
hard-negative outcomes, chapter coverage, evidence gaps, runtime, peak memory,
temporary-media deletion and the exact reason for pass or rejection.
