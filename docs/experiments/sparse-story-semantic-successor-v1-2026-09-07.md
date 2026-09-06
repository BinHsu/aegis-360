# Sparse story semantic successor v1

Status: protocol frozen; synthetic schema/binder implemented; no model or media acquired

## Synthetic implementation checkpoint

`aegis360.sparse_story_semantics` implements the exact closed raw observation,
ordered binder, strict stdout-byte parsing, operational-failure precedence and
failure-bound canonical abstention. Its public success path computes the raw
output hash from strict-parsed bytes; its failure path rebuilds the artifact
from captured bytes and operational flags before binding it. Opaque packet IDs
are restricted to `packet-[0-9a-f]{20}`. Independent implementation audit passed
after raw-hash and failure-state bypasses found in earlier drafts were closed.
Eight focused tests and the complete 568-test suite pass. This checkpoint uses
synthetic JSON only and adds no semantic, model, media or performance evidence.

## Question and claim boundary

Can one bounded semantic observation per cheap-signal event distinguish a
persistent activity or setting change from viewpoint, foreground and capture
nuisances without per-frame VLM inference? The first gate establishes only
model/schema feasibility on known diagnostic packets. A later source-diverse
blind gate may establish held-out event-classification and proposal-recall
evidence. Neither gate grants an exact boundary, chapter map, camera choice,
temporal reorder or render authority.

The rejected RGB and grayscale structural policies remain negative evidence.
Their scores must not become inputs, thresholds, candidate ranks or labels.

## Ownership

- Cheap signals union scene change, motion onset, audio novelty/reaction or
  speech activity, detector/group deltas, track lifecycle and view availability.
  They schedule high-recall review scope only. Magnitudes cannot label, rank
  narrative importance or suppress a distinct event after local deduplication.
- The existing durable lineage packet owns its exact source interval, anchors,
  four-view coverage and private machine evidence. A new exact adapter-visible
  projection exposes only opaque packet ID, chronological row roles, safe media
  refs and anonymous view slots. It removes source/event/time/position, signal
  type/magnitude, expected class, geometry and edit request. The runner must
  prove this projection from the private packet before invoking an adapter.
- A replaceable local adapter emits only the closed observations below or
  abstains. It cannot emit timestamps, identities, confidence, prose, geometry,
  chapter labels, narrative function, candidate views or edit commands.
- A new successor evidence schema and deterministic binder derive one
  conservative event class. Only the provenance, closed-schema, abstention and
  authority patterns of `scene_story_semantics.v1` are reused; that schema
  itself is incompatible because it requires forbidden chapter and narrative
  labels. Typed boundary,
  complete chapter map, global planner and renderer remain later authorities.

## Closed observation contract

Every packet has no more than six chronological four-cardinal composites. The
raw adapter output contains exactly these fields:

| Field | Closed values |
| --- | --- |
| `status` | `observed`, `abstain` |
| `early_state_coherence` | `observed`, `not_observed`, `unclear` |
| `late_state_coherence` | `observed`, `not_observed`, `unclear` |
| `activity_relation` | `same`, `changed`, `unclear` |
| `setting_relation` | `same`, `changed`, `unclear` |
| `anonymous_participant_configuration` | `same`, `changed`, `unclear` |
| `transition_support` | `supports`, `contradicts`, `insufficient` |
| `viewpoint_change` | `present`, `absent`, `unclear` |
| `foreground_rearrangement` | `present`, `absent`, `unclear` |
| `exposure_or_palette_change` | `present`, `absent`, `unclear` |
| `capture_or_projection_artifact` | `present`, `absent`, `unclear` |

Participant configuration describes anonymous visible composition only; it
cannot assert correspondence or identity across rows.

Raw `status=abstain` requires every relation/coherence/nuisance field to be
`unclear` and transition support to be `insufficient`. The binder preserves and
hash-binds every valid raw observation unchanged, then emits a separate closed
`event_class` using this ordered truth table; every unlisted observed
combination derives `event_class=abstain` without rewriting the raw fields:

1. `capture_artifact`: status observed and capture/projection artifact present.
2. `story_change`: status observed; both states coherent; activity or setting
   changed; transition supports; and viewpoint, foreground, exposure/palette
   and capture/projection nuisances are all absent.
3. `no_semantic_change`: status observed; both states coherent; activity and
   setting both same; capture and exposure/palette nuisances absent; and either
   participant configuration is same, or it is changed while viewpoint or
   foreground rearrangement is present.
4. `abstain`: any valid observation not matched above.

A malformed, incomplete or forbidden raw model output is never accepted or
silently stripped. The runner first records a closed operational-failure
artifact whose `reason` is exactly one of `malformed_json`, `schema_violation`,
`forbidden_field`, `missing_anchor` or `invocation_failure`. It contains packet
ID, private-packet SHA-256, adapter-projection SHA-256, model-asset SHA-256,
`prompt_schema_bundle_sha256` for one canonical artifact containing both the
prompt and schema, `raw_output_present` and `raw_output_sha256`. Assign exactly
one reason using first-match precedence: pre-invocation `missing_anchor`, then
`invocation_failure`, `malformed_json`, `forbidden_field`, and finally
`schema_violation`. The final
hash is SHA-256 of the exact captured stdout bytes; when no bytes exist it is
the SHA-256 of the empty byte string and `raw_output_present=false`. The artifact
stores only closed fields and digests, never offending bytes, stderr or free
text. The binder constructs the canonical all-unclear/insufficient raw
abstention and binds both it and `event_class=abstain` to the failure-artifact
SHA-256. Participant configuration alone never manufactures a story change or
chapter.

## Stage A: bounded feasibility

Freeze exactly six known-label diagnostic packets: Old Ghost 205.6-second story
change and 132.4-second no-change; Skiing second-200 story change, 297-second
no-change, 327.25-second stitch/stretch artifact and 386.5-second no-change.
These are a predeclared feasibility/regression set, not held-out accuracy data.
Their labels are intentionally public in this protocol but are absent from the
adapter-visible projection. Stage A therefore makes no hidden-key or held-out
claim. To prevent the public labels from entering inference, its execution
worker receives only the sanitized projections, frozen prompt/schema, frozen
model runtime and an opaque output destination; it has no repository, protocol,
conversation history, label key, prior output or network access. Freeze packet
set, neutral schedule, model asset and prompt/schema before inference.

Run one packet as an operational smoke only, then run the complete six-packet
set serially twice in independent fresh worker processes. The smoke does not
count toward either complete run. Freeze exactly 12 per-packet raw-output hashes
for the two complete runs. Record wall time, process RSS, MLX peak memory, swap
and thermal state on the M4 MacBook Air with 16 GB. The complete runs must
produce byte-identical closed output per matching packet. Malformed output,
missing anchors, any forbidden field or model failure follows the operational-
failure contract and becomes a failure-bound abstention.

There are exactly two story, three no-change and one artifact cases. Both story
cases, all three no-change cases and the artifact must be correct; abstain or
model failure counts incorrect. Outcome precedence is total: invalid lineage,
packet/key composition mismatch, label leakage into adapter-visible input or
forbidden downstream authority yields `invalid`; missing required outputs or
performance measurements yields `inconclusive`; otherwise non-identical reruns
or any incorrect case yields `reject`; otherwise the result is `pass`. No
outcome permits prompt edits on these packets. This stage cannot support
generalization.

## Stage B: source-diverse blind gate

Only after Stage A passes, freeze Skiing, Bellpuig, Gaudeamus and Hundra. For
each source, the proposal universe is every event in its frozen multi-signal
union timeline after overlap-cluster local deduplication only. An event is
eligible when all six packet rows at offsets `-15`, `-3`, `-0.25`, `+0.25`,
`+3` and `+15` seconds are within the source. Order eligible proposals by the
ascending SHA-256 digest of the exact UTF-8 string, with no trailing newline,
`source_sha256|timeline_sha256|stage-b-proposal-v1|event_id`; break a digest tie
by bytewise event ID. Greedily take the first three whose centers are at least
30 seconds from every already selected proposal center.

Build the control universe from the fixed ten-second lattice at 20.0, 30.0,
... seconds through the last lattice point no later than source duration minus
20 seconds. First remove points whose absolute distance from any selected
proposal is less than 30 seconds. Order the survivors by the ascending SHA-256 digest
of the exact UTF-8 string, with no trailing newline,
`source_sha256|timeline_sha256|stage-b-control-v1|timestamp_one_decimal`; break
a digest tie by numeric timestamp, then greedily accept a point only when its
distance from every already accepted control is at least 30 seconds, stopping
after three. Freeze
the exact timeline, dedup clusters, eligible universes, order keys, exclusions
and selected packet IDs in an execution manifest. Fewer than three proposals
or controls for any source makes the run `inconclusive`; there is no replacement
or backfill. The complete set is therefore exactly 24 packets.

Freeze the execution manifest, private lineage packets, adapter-visible
projections, model asset, prompt/schema and two fresh isolated reviewers'
instructions. Reviewers receive only the review media and label all 24 packets;
their output hashes are frozen while their contents remain unavailable to the
model operator. Run exactly one complete model pass and freeze all 24
per-packet raw-output hashes. Each packet's single bound class from that pass
enters the semantic numerator. Only then may the coordinator open the reviewer
outputs and proposal/control mapping.

Adequacy requires all 24 reviewer pairs to agree on binary story/no-change,
at least six of each overall, both classes in at least two sources and at least
four nuisance no-change packets. A packet belongs to the nuisance denominator
only when both reviewers label it no-change and both independently mark
`viewpoint_change=present` or both independently mark
`foreground_rearrangement=present`; agreement on one of those fields suffices.
Artifact, abstention, disagreement or inadequate balance makes the run
inconclusive; it does not authorize more samples.

Let `N_story`, `N_no_change` and `N_nuisance` be the adequate unanimous reviewer
denominators. Proposal recall passes only when proposed story packets divided
by `N_story` is at least `5/6`, and every source containing a story packet has
at least one proposed story packet. Semantic discrimination passes only when
correct story predictions divided by `N_story` is at least `5/6`, correct
no-change predictions divided by `N_no_change` is at least `5/6`, and correct
nuisance-negative predictions divided by `N_nuisance` is at least `3/4`.
For the nuisance numerator, a prediction is correct exactly when the binder
emits `no_semantic_change`; matching the reviewers' nuisance subtype is not
required.
Model failure, malformed output, artifact classification or abstention counts
incorrect against every applicable adequate denominator.

Outcome precedence is fixed. Invalid lineage, leakage before reveal,
unscheduled inference or forbidden authority yields `invalid`. An adequacy or
selection-capacity failure yields `inconclusive`. With adequate data, both
proposal recall and semantic discrimination must pass for overall `pass`;
otherwise the result is `reject`. Evaluate categorical results only; do not
search a numeric threshold, discard hard packets or revise the prompt.

## Stop conditions

Reject cheap-signal recall when its frozen Stage B fraction misses `5/6` or any
story-bearing source has zero recall. Reject semantic discrimination when either
binary class or nuisance specificity misses its frozen bound. Mark the run
invalid if inference consumes unscheduled frames or emits boundary, camera,
time-reorder or render authority. Gradual changes missed by every cheap signal
remain an explicit recall gap even if the semantic classifier passes.
