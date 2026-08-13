# Interest model

Status: Active design; signal weights are hypotheses

## Editorial objective

Approximate what an ordinary first-time viewer would want to see while
preserving context and avoiding uncomfortable camera behavior. A viewing
candidate may be a person/object track, a group or interaction region, the
forward direction, or an environmental/context view.

## Initial explainable evidence

- person/object presence; detector confidence remains perception evidence;
- track persistence and visibility;
- motion or action change, not raw motion magnitude alone;
- forward-motion prior for first-person travel footage;
- scene novelty and repetition;
- composition/viewport fit;
- continuity with the incumbent subject or context.

Each signal has a name, raw value, normalization method, weight and provenance
in the decision trace. Missing evidence is explicit. Motion must not dominate
quiet but meaningful subjects, and high background flow must not automatically
become the subject.

Persistence is provenance-gated. Nearest-neighbor continuity of generic
attention/objectness saliency has zero raw and normalized editorial
persistence even when its diagnostic age grows. Human rectangles and
candidates carrying an explicit tracker identity may earn persistence. This
prevents a cheap geometric association from receiving the same editorial
advantage as identity-aware tracking, without coupling the rule to a backend.

## Candidate generation

Generate a small, bounded set per decision interval: persistent subject views,
useful group views, forward/context view, and an incumbent continuation. Merge
near-identical spherical directions. Candidate intervals may begin at regular
analysis timestamps or detected events; the choice is tested rather than
assumed.

## Deferred and newly required signals

Owner rejection of the first person-centered semantic render demonstrates that
a whole-body person box is insufficient when visible people are speaking. A
bounded next experiment may use face/upper-body location and mouth motion to
form a group composition. Mouth motion alone is not active-speaker identity;
audio/video agreement and the audio channel convention must be established
before granting an active-speaker signal.

Gaze, detailed action recognition, face identity, personalization and trained
end-to-end ranking remain deferred unless later benchmark failures demonstrate
their necessity.

`aegis360.scene-context.v2` is the bounded interface for a human review or
local VLM. Geometry first declares person, group and context proposals; each
group references two or more declared person proposals without asserting
identity. Review may select one proposal with a matching group/single/context
scope, or return uncertain. The contract has closed evidence flags and no free
text, identity, image, embedding or renderer geometry. Deterministic spherical
geometry remains responsible for the actual shot. V1 is rejected because it
required review to compose cross-time person IDs instead of selecting a
geometry-owned group proposal.

Window aggregation declares proposal-local `person-slot` members from the
minimum simultaneously observed group size. Slots express coverage only; they
are not tracks or identities. A group proposal references those slots, and the
context reviewer selects the proposal as a unit.

Face evidence is a composition hint, not a camera target. In the first real
group window, replacing the body-group pitch with the only detected face pitch
pulled the view upward enough to crowd a second visible member against the
lower frame edge. The POC therefore limits face-derived vertical correction to
5 degrees. This is a tunable guard, not a validated product default; future
group extents or upper-body evidence should replace it when available.

Local-model integration has two boundaries. A backend-specific offline runner
produces only the closed decision fields; the generic importer independently
hashes the exact model asset, binds the decision to geometry-owned proposals,
validates scene-context v2 and writes atomically. The importer is not inference
evidence and does not make an unselected model operational.

The MLX runner constrains scope and candidate together inside mutually
exclusive JSON-schema `anyOf` branches; grammar-valid independent enums are
insufficient. With no audio input, the grammar permits only `unknown` for
speech-audio evidence. The validated 2.2B result may select a proposal, but its
fine context-class label carries no accepted scoring weight until repeatability
and held-out accuracy are established.

An uncertain decision with no selected candidate is an explicit abstention,
not permission to expose an unselected group. The window planner emits only
deterministic `context:forward` for that interval and records
`deterministic_context_fallback`. A fixed-forward result cannot pass the
pose-differentiation gate or support an auto-directing quality claim.

## Acceptance criteria

- Every chosen view can be explained from stored evidence and planner costs.
- Signal ablations expose whether forward, motion or detector confidence is
  dominating unexpectedly.
- Candidate generation includes acceptable directions for manually reviewed
  important events in the benchmark excerpts.
- Scores are deterministic for fixed inputs, models and configuration within
  documented backend limits.
