# Apple SoundAnalysis reaction-event gate — 2026-08-15

Status: Bounded reaction candidates accepted; no camera-cut authority

## Question

Can an OS-provided, offline classifier expose applause timing in the licensed
Gaudeamus benchmark without treating volume or a sound label as editorial
ground truth?

## Contract

`scripts/run_apple_sound_events.py` extracts at most 300 seconds of temporary
mono 44.1 kHz PCM, compiles the native gate, runs Apple's built-in
`SNClassifierIdentifierVersion1`, validates a closed artifact, and deletes the
PCM. Durable output contains no source path, audio or transcript. Only `music`,
`applause`, `clapping` and `cheering` are retained. Confidence is model evidence,
not utility, sound direction or source identity.

`scripts/build_reaction_intervals.py` requires applause and clapping to each
reach 0.5 in at least two overlapping classifier windows. These correlated
labels come from one model, so the threshold remains a POC hypothesis. An
interval is only a candidate for later visual/role validation and cannot
authorize a camera cut.

## Real result

The 128-second Gaudeamus audio run completed in 6.2 seconds including PCM
extraction and Swift compilation. SoundAnalysis emitted 84 three-second windows
at 50% overlap. The bounded aggregation produced:

- 9.0–15.0 seconds: 3 supporting windows; peak applause 0.848849 and clapping
  0.803971.
- 109.5–124.5 seconds: 9 supporting windows; peak applause 0.776286 and
  clapping 0.894515.

Four-view visual inspection places the intervals at the performance opening
and ending, but low source resolution does not establish visible per-person
clapping. A separate 127-second six-view detector run completed in 23.601
seconds with 579 person boxes. Person evidence persists through most of
109.5–118.5, nearly disappears by 118.5–124.5 and is absent at 124.5–127,
matching the title-card transition. The detector finds no people in the distant
audience viewport, so it may bound live-scene availability but cannot validate
an audience reaction shot.

## Decision

Retain the two path-free reaction candidates. Next generate deterministic
context-view geometry, bind human/model roles only to declared candidates, and
intersect reaction timing with live-scene availability. Do not add these scores
to the current greedy weights or render a reaction edit yet.

## Role-bound directing follow-up

A deterministic four-cardinal grid owns all camera geometry. The owner's rule
binds `context:cardinal:3` (-90 degrees) to primary performance and
`context:cardinal:1` (+90 degrees) to audience reaction through the exact grid
SHA-256; the role artifact contains no camera geometry. Any-view person evidence
forms one broad live-scene interval at 11.5–119.0 seconds. Intersecting it with
sound candidates produces the closed five-segment timeline: primary 0–11.5,
reaction 11.5–15, primary 15–109.5, reaction 109.5–119, primary 119–127.

Primary-only and planned v3 proxies use the same VideoToolbox/AAC contract.
Both are 960x540 yuv420p at constant 15 fps, 1,905 frames and 127.000 seconds;
both audio streams are 127.002 seconds. Agent contact-sheet review confirms the
declared directions, visible hard cuts, return to the primary view and no
obvious projection/codec defect. Opening and closing titles remain source
content. Editorial timing now requires owner review.

Owner review rejected both v3 peers because the shared -90-degree/110-degree
primary view cropped too much of the choir and needed to move right. Geometry
frame probes separated center from width: at yaw -70 degrees, 120-degree HFOV
retains the ensemble while avoiding the extra distortion/empty table of 130 or
140 degrees. Audience probes retain +90 degrees as better centered than +100 or
+110. A checksummed declared-view grid v2 therefore owns independent geometry:
primary -70/+5/120 and reaction +90/0/120 degrees. Roles still carry no pose.

The v4 wide peers preserve the same reaction timeline and encoder contract.
Both remain 1,905 frames/127 seconds. Agent contact-sheet review finds the choir
materially more complete, the audience view unchanged, and no new projection or
codec defect. Owner review remains required.

Owner review then found the 11.5-second cut abrupt because the opening title
animation led directly into the audience. The cause was interval intersection:
the sound event began at 9 seconds, before live-scene availability at 11.5, and
the planner joined it mid-event. Reaction-shot plan v2 now requires the event
onset itself to occur inside an already-live interval. The opening event is
therefore suppressed rather than truncated; the ending event remains valid.

Planned v5 has three segments: primary 0–109.5, audience reaction 109.5–119,
and primary/title 119–127. It remains 1,905 CFR frames with the same audio and
encoder contract. Agent inspection confirms the opening animation now flows
directly into the corrected choir view, while the ending audience cut remains.

On 2026-08-15 the owner accepted planned v5 as a satisfactory directing result.
This accepts the corrected choir composition, suppression of the opening
mid-event cut, the 109.5–119 audience reaction and the return to titles. It does
not validate generic applause thresholds, automatic performer/audience role
inference, cross-scene accuracy or active-speaker behavior.

External evidence:

- `outputs/sound-events/gaudeamus-full-apple-v1/events.json`
- `outputs/reaction-intervals/gaudeamus-full-apple-v1-threshold-p5/intervals.json`
- `outputs/semantic-events/gaudeamus-full-six-view-yolox-v2/`
- `outputs/context-view-grids/gaudeamus-full-four-cardinal-v1/grid.json`
- `outputs/editorial-view-roles/gaudeamus-full-owner-v1/roles.json`
- `outputs/live-scene-intervals/gaudeamus-full-person-gap1p5-v1/intervals.json`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v1/plan.json`
- `outputs/reaction-preview/gaudeamus-full-{primary-only,planned}-540p-v3/`
- `outputs/context-view-grids/gaudeamus-full-declared-v2/grid.json`
- `outputs/editorial-view-roles/gaudeamus-full-owner-v2/roles.json`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v2-wide-primary/plan.json`
- `outputs/reaction-preview/gaudeamus-full-{primary-only,planned}-540p-v4-wide/`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v3-live-onset/plan.json`
- `outputs/reaction-preview/gaudeamus-full-planned-540p-v5-live-onset/`

## Candidate-scoped hardening

The accepted Gaudeamus result exposed a contract defect: an any-view live-scene
interval could authorize an audience candidate that was not itself visible.
Plan v3 replaces that broad proxy with a checksummed candidate-availability
artifact. Unlisted candidates have no implicit availability. The plan and
renderer now rehash and validate the exact grid, roles, reaction intervals and
candidate availability; a stale or substituted input fails closed. The
renderer also trims audio at the grid's absolute source window, not at zero.

The corrected Gaudeamus replay retains the accepted three segments and reasons,
so the hardening changes evidence authority without changing the owner-approved
edit. Its immutable external outputs are:

- `outputs/candidate-availability/gaudeamus-audience-v1/availability.json`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v5-candidate-availability-trace/plan.json`
- `outputs/reaction-preview/gaudeamus-full-planned-540p-v6-p0-rebind/`

## Held-out moving-procession result

`Hundra knektars marsch på Forum Vulgaris` is an independent 227.232-second,
1920x960 ERP source licensed CC BY-SA 4.0. The full Apple run yields one strong
candidate at 217.5–226.5 seconds: five supporting windows, peak applause
0.782600 and peak clapping 0.801312. Human contact-sheet review establishes the
camera as part of the procession: yaw 0/110 is the forward primary view, while
yaw -45/110 centers the left-side audience without the flag occlusion at +90.
Incidental minors remain background and are not eligible subjects.

A nonzero 210–226.5-second grid produces two segments: primary until 217.5,
then candidate-scoped audience until the window ends. Equal-contract baseline
and planned outputs both contain 248 video frames (16.533 seconds) and 516 AAC
frames (16.512 seconds). Initial agent review incorrectly promoted removal of a
near-field flag to improved reaction framing. Owner review rejected that claim.
A denser paired replay at one-second spacing shows yaw 0 retaining responsive
spectators on both sides and better preserving the procession relationship;
yaw -45 replaces the flag with a large tent and does not expose a clearer
reaction. The correct result is primary-only: sound timing plus candidate
availability does not establish relative editorial gain or authorize a cut.

This is a useful held-out negative, not cross-scene directing accuracy. Add a
fail-closed relative-gain comparison between current and proposed views before
another reaction cut. The legacy fixed/auto pre-review script does not consume
reaction bundles; a reaction-specific mechanical gate is also still needed.

External evidence:

- `outputs/sound-events/hundra-full-apple-v1/events.json`
- `outputs/reaction-intervals/hundra-full-apple-v1-threshold-p5/intervals.json`
- `outputs/context-view-grids/hundra-210-226p5-declared-v1/grid.json`
- `outputs/editorial-view-roles/hundra-210-226p5-v1/roles.json`
- `outputs/candidate-availability/hundra-audience-v1/availability.json`
- `outputs/reaction-shot-plans/hundra-210-226p5-v1/plan.json`
- `outputs/reaction-preview/hundra-210-226p5-{primary,planned}-v1/`

## Relative editorial-gain gate

Reaction plan v4 adds a fifth immutable input,
`aegis360.reaction-view-gain.v2`. A human or local-VLM adapter may only mark an
exact declared reaction interval `promote` or `abstain`; current and proposed
candidates are derived from the checksummed role artifact. It cannot emit
camera geometry, free text, identity or a new candidate. Missing decisions
default to abstain. The renderer revalidates the gain artifact and its exact
SHA-256 with the other four evidence inputs, then rebuilds the unique expected
plan. A manually altered candidate, timing or reason therefore fails even when
all evidence hashes remain valid.

V1 is rejected for new plans because it allowed `local_vlm` without mandatory
model ID/SHA provenance. V2 requires those fields for a model and explicit null
values for a human reviewer.

The owner decisions form one positive and one negative replay. Gaudeamus
promotes the 109.5–124.5 event and reproduces the accepted three-segment plan.
Hundra abstains on 217.5–226.5 and produces one primary-only segment. Renderer
replays are decoded-identical to their accepted reference outputs:

- Gaudeamus: 1,905 video frames and 5,470 audio frames; reference and v4 video
  SHA-256 `5294c3f1eea951f2e182218d8bba2f2806653d5cfad54f0da6b6c21384646e88`;
  audio SHA-256 `e7a67f57838cd2d816d9240c09b4e3c6d3fea0b4e1bfb6dd6fd8f8bbb2112a06`.
- Hundra: 248 video frames and 516 audio frames; primary and v4 video SHA-256
  `52faaecc5a61ae814c36a6a54a96c8f996a0fafb5af0bb403d21a420a3350b8f`;
  audio SHA-256 `7f70ada07572497417e98afd6e694ab2d9cb9b26fc9b1f8a306fc99404b9992b`.

This establishes the fail-closed integration boundary, not an automatic
relative-gain classifier. External evidence:

- `outputs/reaction-view-gain/gaudeamus-owner-v2/gain.json`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v7-gain-v2/plan.json`
- `outputs/reaction-preview/gaudeamus-full-{primary,planned}-540p-v8-gain-v2/`
- `outputs/reaction-view-gain/hundra-owner-v2/gain.json`
- `outputs/reaction-shot-plans/hundra-210-226p5-v3-gain-v2-abstain/plan.json`
- `outputs/reaction-preview/hundra-210-226p5-{primary,planned}-v3-gain-v2/`

## Reaction-preview mechanical gate

`scripts/check_reaction_pre_review.py` now validates v4 evidence and reconstructs
the plan before comparing equal-lineage primary/planned bundles. It checks trace
bindings, encoder metadata, decoded stream probes and decoded audio identity.
For `promote`, video must differ and declared pose/duration must exceed explicit
8-degree/2-second floors. For `abstain`, decoded video must be identical. These
are differentiation checks, not editorial scoring; paired visual review remains
mandatory before any new owner request.

Both real gates pass. Hundra has zero promoted segments and decoded identity.
Gaudeamus has one 9.5-second promoted segment with a 160-degree maximum declared
pose difference, identical decoded audio and distinct decoded video. Reports are
atomic, refuse overwrite and contain no paths or pixels:

- `outputs/reaction-pre-review/hundra-v3-gain-v2/report.json`
- `outputs/reaction-pre-review/gaudeamus-v8-gain-v2/report.json`
