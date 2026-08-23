# Blind director-intent protocol v1

## Goal

Test what editorial intent an ordinary viewer infers without asking whether a
specific intended answer was understood. Presence, mechanical differentiation
and an informed owner's ability to recognize a disclosed trick are not passes.

## Separation

The review media uses a neutral identifier. The intended reading and scoring
key remain in a separate checksummed artifact not shown before the response.
The renderer/pre-review agent may know the key; the viewer and questionnaire
must not. A contaminated question is removed before scoring rather than
retrofitted to the answer.

## Question order

Ask once, after uninterrupted playback and before showing a baseline:

1. What do you think the director most wanted you to notice?
2. What kind of experience or story did the clip seem to present?
3. How did the beginning and later shots relate to each other?
4. What would you expect to happen next?
5. Did anything feel joined incorrectly, temporally confusing or accidental?

Do not mention a subject, destination, foreshadow, reaction, chapter or
alternative interpretation in the questions. Do not ask yes/no comprehension
questions until the open responses are frozen.

## Scoring

- `2`: unaided response captures the hidden editorial relationship or intended
  expectation.
- `1`: response identifies a relevant focus but not the relationship.
- `0`: plausible generic reading with no evidence the edit communicated its
  specific intent.
- `-1`: viewer reports an erroneous join, broken playback or temporal confusion.

Confusion is reported separately and cannot be erased by a correct guess. One
viewer is a protocol smoke test, not preference or accuracy evidence. A later
evaluation randomizes neutral labels and presentation order across viewers.

## Skiing pilot limitation

The owner was told that the source is the Skiing benchmark before playback.
Genre/category inference is therefore contaminated and excluded. Focus,
relationship, expectation and confusion remain hidden-intent questions. This
hand-authored clip validates the protocol only; it is not automatic-planner
accuracy evidence.

## Pilot result

The independent key was sealed before the response at SHA
`576029f793a6e0a6898fcc3abad0be14ec5c36c0eb52491b070ba1ca6db2a41f`.
After one uninterrupted viewing, the owner identified skiing, snow scenery,
the progression toward other skiers and an expectation of more direct skiing
action. No bad join or temporal confusion was reported, and the edit was
acceptable.

The frozen key required a people/gathering-to-terrain relationship plus an
expected shared departure for score 2. The response did not infer that full
relationship, so the result is `1 / partial_focus`, confusion false. The exact
response artifact SHA is
`035798c1828094c2db50a8f78c662835e7c6f2013a1771985f0c521f85a5a833`.
This supports protocol usefulness and edit legibility, not full-intent
communication or planner accuracy.

After the blind response was frozen and the key opened, the owner viewed the
same-contract baseline second. Baseline won both perceived direction and
natural/watchable preference because the lift and skiers established stronger
action expectations and the transition was smoother. Candidate A's switch was
slightly abrupt, though both clips remained acceptable and human-feeling.

`aegis360.segment-editorial-gain.v1` binds that result to the exact two media
hashes. Its closed decision is `retain_baseline`; candidate eligibility is
false for stronger causal cues, smoother transition, no preference gain and an
abrupt switch. This is a benchmark negative for forced semantic reframing.

The failure was an integration-path failure, not evidence that ordinary camera
motion is undesirable. Candidate A came from the bounded symbolic story
planner, which can switch to a stable primary at a chapter boundary but applies
no numeric transition cost. Under the existing global-DP policy, an otherwise
equal 90-degree cut-away-and-return is rejected: it incurs 1.0 fixed cost plus
approximately 0.314 angular cost, after first needing 0.5 minimum advantage.
The renderer now requires an explicit symbolic-experiment opt-in; such output
cannot silently stand in for a production-planner candidate.
