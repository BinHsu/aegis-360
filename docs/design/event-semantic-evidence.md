# Event semantic evidence

Status: Implemented contract; no model selected

## Boundary

`aegis360.event-semantic-evidence.v1` is the only durable output expected from
a sparse local semantic adapter. It binds one exact Event Review Packet and an
exact adapter config. It records observations, not an edit decision.

An observed result must cover every candidate that appears in the packet,
once and in first-appearance order. For each it may classify only visibility
(`clear`, `partial`, `obstructed`, `unknown`), event relevance (`primary`,
`supporting`, `unrelated`, `unknown`) and temporal consistency (`stable`,
`changing`, `unknown`). Event class and current/proposed relationship also use
closed enums. The schema contains no confidence number because model outputs
are not assumed calibrated.

`abstain` is a first-class result and must carry unknown event/relationship
values with an empty observation list. This prevents an adapter from hiding
claims behind an uncertainty flag.

## Ownership

- The packet owns event scope, timestamps and eligible candidate IDs.
- The checksummed context grid owns camera geometry.
- The semantic adapter owns only closed observations and abstention.
- A future evidence-to-utility adapter owns deterministic score conversion.
- The global planner owns all cut/view decisions and transition costs.

Model ID and exact model-asset SHA-256 are mandatory. Free text, paths, media,
names, identity, geometry, new candidates and renderer commands are forbidden.
The constrained raw-output JSON schema narrows decoding; the binder remains
the authority and rejects missing, invented or reordered candidates.

## Evidence-to-utility

`aegis360.event-candidate-utility.v1` applies a checksummed policy to each
closed observation. The committed POC policy keeps separate relevance,
visibility, temporal-consistency and proposed-view relationship components.
It emits the components and total for both current and proposed candidates,
while explicitly declaring that no candidate, transition or dwell decision
has been applied.

Abstention leaves current eligible at neutral utility and makes proposed
ineligible. This is the deterministic fail-closed route. The weights are
tunable hypotheses rather than probabilities; changes produce a new policy
checksum and can be evaluated without changing semantic evidence.

The next gate is event-to-global-planner integration using a configurable
minimum advantage plus transition, dwell and repetition costs. Do not acquire
or tune a model before that deterministic path and benchmark-label evaluation
are defined.

## Neutral scene-story evidence

Reaction evidence v1 remains unchanged. Neutral scene events use the separate
`aegis360.scene-story-review-packet.v1` and
`aegis360.scene-story-semantics.v1` contracts because two isolated boundary
frames and reaction-specific classes cannot represent story context.

The scene-story packet supplies bounded local temporal context, whole-video
position and neighboring event summaries. Four cardinal source viewports are
composited into one image per anchor so a semantic adapter receives at most six
images. Its closed evidence separates structural role, narrative function,
change type and ordinary-viewer value. None chooses a candidate view or edit.
The global planner owns chronological comparison and must combine story role
with independent view relevance and transition costs.

`aegis360.story-planner-constraints.v1` is the candidate-free integration
boundary. It maps structural roles to change/continuity/closing and repetition
symbols, plus viewer value to coverage priority. It cannot choose geometry or
apply numeric costs. A future planner revision may consume it only alongside
independently checksummed candidate-view relevance.

Candidate relevance is segment-scoped, not boundary-event-scoped. A story
segment timeline partitions the source at retained cuts; its packet samples
only within one segment. `aegis360.segment-view-relevance.v1` records ordered
candidate visibility, relevance and temporal consistency or strict abstention.
It cannot select a candidate. Boundary constraints and segment relevance meet
only inside the global planner.

The first bounded symbolic planner is a fail-closed integration baseline:
missing/abstained relevance retains the current view, continuity keeps a usable
current candidate, chapter change may adopt a stable primary, and closing
holds. It applies no numeric cost and cannot support footage outside its exact
segment-aligned window. The production planner remains the global DP required
by ADR 0006. Its plan therefore declares `production_eligible: false`, and its
renderer requires an explicit `--allow-symbolic-baseline` experiment opt-in
for planned output. A chapter boundary and stable primary alone cannot promote
a production candidate without numeric advantage and transition costs.

## Chapter map before temporal reordering

Story-boundary observations and the cut-partitioned segment timeline do not by
themselves form a chapter map. A chapter map must cover the complete selected
story window, assign every segment to exactly one ordered chapter, bind chapter
starts and ends to observed evidence, and expose every abstention or unresolved
boundary. It must not derive certainty from candidate-view relevance.

Under ADR 0011, only an independently validated complete chapter map may
authorize a bounded future-chapter foreshadow. Missing coverage, an unresolved
boundary, or a merely local chapter label preserves chronology. This repository
does not yet implement that chapter-map contract, so the current planner has no
authority to reorder source time.

The minimal temporal form is `[future prefix][complete chronological body]`.
The prefix duplicates rather than moves the payoff interval; the body has no
other source-time reversal. The eventual plan must declare the chapter-map and
policy checksums, prefix source interval, destination chapter, return point and
fallback reason. Exact rebuild validation must reject any mutated interval or
lineage.

`aegis360.chapter-map-foreshadow-eligibility.v1` is the next candidate-free
gate. It requires an exact-map qualification with a source-verified or held-out
calibrated evidence hash, at least two chapters and a later destination
chapter. Abstention or missing destination returns `eligible: false`. A pass
only permits the next planner to consider one prefix; it still selects no
interval, view, transition or renderer command.

Relative gain must also exist outside reaction-specific edits. The generic
`aegis360.segment-editorial-gain.v1` binds an exact candidate/baseline media
pair to closed human, agent or local-model evidence. `retain_baseline` requires
explicit no-preference-gain evidence and makes the candidate ineligible. It is
a benchmark label boundary, not a production human-approval dependency or a
substitute for causal-continuity signals in the automatic utility model.
