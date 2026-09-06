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

`aegis360.sparse_story_projection` now implements the subsequent pure-JSON
projection gate: exact private structure and canonical hashes, complete 1/6/24
packet-set binding, domain-separated salted IDs and presentation order, closed
anonymous projections and exact rebuild. Four focused tests plus the complete
572-test suite pass after independent audit caught and closed boolean row-number
acceptance and same-packet ID/order HMAC collision. It does not yet validate a
media tree or execution isolation.

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

## Sanitized projection synthetic gate

Before any media or model run, implement a pure-JSON projection from a complete
set of structurally validated private packets to a role-neutral public index.
This gate proves exact sanitization only. A prior, separate lineage gate must
prove each private packet from the frozen execution manifest, timeline and grid;
changing a private hash or time creates a different input and is outside the
projection gate's authority. The execution manifest freezes only pre-projection
selection identities and order, never opaque IDs or a public-index hash, so its
hash cannot depend circularly on the projection.

The private packet schema is `aegis360.sparse-story-private-packet.v1` with
exact top-level fields `schema_version`, `source_id`, `selection`, `inputs`,
`center_source_time`, `rows`, `privacy` and `authority`. `selection` contains
only `role` (`proposal` or `control`), `original_event_id` (string for proposal,
null for control) and `original_signal_ids` (a non-empty unique string list for
proposal, empty for control). `inputs` contains exactly the four SHA-256 values
`execution_manifest_sha256`, `source_sha256`, `event_timeline_sha256` and
`context_view_grid_sha256`. Center and row source times are reduced positive-
denominator rational `{numerator, denominator}` objects. `rows` has exactly the
six numbered roles below in order; each row contains only `row_number`,
`row_role`, `absolute_source_time` and `cardinal_views`. `cardinal_views` is the
same ordered four-item list on every row; each item contains exact private
`candidate_id`, `yaw_degrees`, `pitch_degrees` and
`horizontal_fov_degrees`. Rows equal center plus the exact rational offsets
`-15`, `-3`, `-1/4`, `+1/4`, `+3`, `+15` seconds without clamp or deduplication;
negative row times are invalid. Proposal and control packets have the same
shape; controls use null event ID and an empty signal list rather than inventing
a timeline event.

`source_id`, every non-null original event/signal ID and every candidate ID are
nonempty strings matching `^[A-Za-z0-9._:+/-]+$`. Candidate IDs are unique and
the exact same ordered four IDs occur on every row. Booleans are not numbers;
geometry values are finite integers or floats with yaw in `[-180, 180)`, pitch
in `[-90, 90]` and horizontal FOV in `(0, 180]`. Original signal IDs are unique.
Every rational is reduced, its denominator is positive, and center/row source
times are nonnegative.

Private `privacy` is exactly `contains_source_path=false`,
`contains_pixels=false`, `contains_audio=false`,
`contains_expected_class=false`, `contains_reviewer_result=false`. Private
`authority` is exactly `lineage_input=true`, `semantic_observation=false`,
`exact_boundary=false`, `chapter_map=false`, `camera=false`, `reorder=false`,
`render=false`. The private packet SHA-256 is over sorted, compact,
ASCII-escaped JSON encoded as UTF-8 with no trailing newline.

The coordinator accepts an exact 64-character lowercase hexadecimal secret
salt. The HMAC key is exactly the 32 bytes obtained by decoding that hex, not
the 64 ASCII characters. For each private packet it computes two full lowercase-
hex HMAC-SHA256 values over exact UTF-8 messages with no newline:
`id|successor-packet-v1|execution_manifest_sha256|private_packet_sha256` and
`order|successor-packet-v1|execution_manifest_sha256|private_packet_sha256`.
It exposes only `packet-` plus the first 20 ID-HMAC hex characters, sorts the
complete packet set by full order HMAC with full ID HMAC as tie-break, and
exposes only the resulting one-based presentation ordinal. Salt and full HMACs
remain private. The set-level builder rejects any duplicate private-packet hash,
full HMAC or truncated packet ID. Plain hashes of enumerable event/time values
are forbidden.

The adapter-visible projection is exactly:

```text
schema_version: aegis360.sparse-story-adapter-index.v1
packet_count: exact length of the complete private set
packets:
  presentation_ordinal: 1..packet_count
  projection:
    schema_version: aegis360.sparse-story-adapter-projection.v1
    packet_id: packet-[0-9a-f]{20}
    rows: exactly six rows
      row_number: 1..6
      row_role: early_far, early_near, transition_before, transition_after,
                late_near, late_far
      media_ref: media/<packet_id>/row-01.png ... row-06.png
      views: exactly [view-1, view-2, view-3, view-4]
```

Every projection's `privacy` is exactly these false-valued keys:
`contains_source_id`, `contains_event_id`, `contains_signal`,
`contains_source_time`, `contains_position`,
`contains_proposal_control_role`, `contains_lineage_hash`,
`contains_signal_evidence`, `contains_score_or_confidence`,
`contains_expected_class`, `contains_identity`,
`contains_real_candidate_id`, `contains_geometry`, `contains_chapter_label`,
`contains_narrative_function`, `contains_prose`, `contains_edit_request`.
Every projection's `authority` is exactly `semantic_observation_input=true`,
`exact_boundary=false`, `chapter_map=false`, `camera=false`, `reorder=false`,
`render=false`. The public index adds no other top-level fields. Each projection
SHA-256 used by the evidence binder is over that projection's sorted, compact,
ASCII-escaped JSON encoded as UTF-8 with no trailing newline.

The projection builder must also receive the exact ordered private-packet
SHA-256 list already emitted by the prior lineage gate. It is nonempty and has
exactly 1 item for the Stage A smoke, 6 for either complete Stage A run, or 24
for Stage B. The supplied private packet sequence must match that list exactly,
and every packet must contain the same `execution_manifest_sha256`; omission,
addition, duplication or reorder fails. The entire public index uses the same
sorted compact ASCII-escaped UTF-8 JSON with no trailing newline; its SHA-256 is
computed externally over those bytes and never embedded in the index.

Rows retain chronology but expose no timestamp or offset. Views retain stable
within-row slots but expose no candidate identity or direction. Media refs are
relative, path-normalized, contain only the opaque packet ID and fixed row
number, and permit no symlink or extra file at the later media-tree gate. Exact
closed projection equality is the sole leakage rule: no independent substring
or private-value blacklist is used, because numbers and strings can coincide
innocently. The set-level validator structurally validates every private packet,
recomputes its canonical hash, both HMACs, order, IDs and complete public index,
then requires exact equality.

The synthetic gate passes only when exact rebuild is byte-stable; mutations,
row reorder/drop/add, unsafe refs, salt/hash mismatch, extra public fields and
opaque-ID collisions all fail closed. This gate grants projection
and adapter-input authority only. PNG sanitization, closed media-tree proof,
minimal process environment, repository/filesystem isolation, network denial,
stdout capture and model invocation remain separate runner gates.

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
and selected proposal event IDs plus selected control timestamps in their pre-
projection selection order in an execution manifest. Fewer than three proposals
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
