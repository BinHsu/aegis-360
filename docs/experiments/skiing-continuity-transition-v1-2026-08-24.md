# Skiing continuity transition v1

## Question

Can sparse source evidence explain why the 35-second Skiing baseline was
preferred to candidate A without encoding that preference or selecting a view?

## Exact scope

The original render command was recovered from the local Codex session. Both
clips use source 380–415 seconds. Baseline uses cardinal 0 throughout; A uses
cardinal 3 (yaw -90) for 380–390, then cardinal 0 for 390–415. The boundary is
therefore exact, not inferred from output pixels.

The two segments use declared samples at 382, 385, 388 and 395, 402.5, 410
seconds. Temporary four-cardinal contact sheets were independently inspected
and deleted. An initial FFmpeg loop omitted `-nostdin`; FFmpeg consumed decimal
timestamps from the loop. That partial output was rejected and all six frames
were rebuilt with `-nostdin` before review.

## Closed result

The observed narrative association is transport context followed by terrain
destination. It does not claim that skiers persist, depart together or cause
the later view.

- cardinal 0: partial transport, clear terrain, partial preservation;
- cardinal 1: clear transport, partial terrain, partial preservation;
- cardinal 2: clear transport/terrain and preservation, but terrain faces more
  toward ridge/uphill than a proven downhill destination;
- cardinal 3: transport absent, terrain clear, association breaks.

Cardinal 0 at 385 seconds is partly obscured by a lens droplet. At 388 seconds
transport has disappeared in every direction. Object continuity and physical
causality are not established.

## Deterministic transition utility

The neutral policy maps endpoint evidence and same-candidate preservation to a
complete 4x4 matrix. Cross-candidate cells receive no preservation value. It
produces cardinal 0→0 `0.5 + 1.0 + 0.5 = 2.0` and cardinal 3→0
`-1.0 + 1.0 + 0.0 = 0.0`.

This matches the direction of owner preference without a Skiing ID, baseline
label or edit decision in policy. It is one agent-labeled benchmark, not
population calibration or automatic semantic accuracy.

External path: `outputs/causal-continuity/skiing-a-v1/`. SHA-256:

- observed config: `655c74fada6fdffd26793738cf0d024e05e7e4bf8eb8bc5fd4eb515836e59ebb`;
- observed evidence: `bc34aac9c5395c1cee62243a6affeb4d671998d844c0a1c3d49ef1cefee55858`;
- transition utility: `e841501499986c6e150cef924cb06651cf9c37d415872225290d716c13a942d5`.

Global story DP v2 now consumes the exact matrix. A closed synthetic ablation
shows the intended wiring: with a zero matrix the competing segment utility
causes the A-like switch; adding observed same-view preservation retains the
baseline-like path. This proves DP integration, not Skiing semantics. A real
Skiing plan still awaits complete per-segment relevance utility, so this
checkpoint authorizes no render.

## Real planner replay

Independent exact-sample review abstains on segment 0000: its 382/385-second
lift and staging content becomes open alpine terrain by 388 seconds, so one
segment-wide primary would conflate two states. Segment 0001 has cardinal 0 as
the stable clear primary; cardinal 1 is low and cardinals 2/3 are supporting.
The resulting real v2 plan retains cardinal 0 for both segments. Its objective
is 5.5: 3.5 segment utility plus 2.0 continuity utility. A zero-continuity
replay retains the identical path at objective 3.5. Thus continuity supports
the result but is not decision-critical in this replay.

The planner SHA is
`b3ab2344e905190acd3ed2cdff9b2320c1f3abaec47906b0f3e079377f3ae3bb`.
Transient six-sample audit pixels were deleted. A 385.5–387.5-second local
probe finds a continuous rapid semantic transition, not a hard cut; the old
hand-authored 390-second boundary is late. Corrected boundary evidence and
rebuilt lineage are required before another production-eligible render.

The repository now has a pure, closed continuous-onset candidate contract for
this class of signal. Synthetic tests cover sustained onset, hysteresis, single
spikes, ordering, cadence, privacy and exact rebuild. It has no media runner or
calibrated Skiing policy yet and cannot alter the timeline.

The upstream frame-difference artifact/parser now normalizes YAVG by 255 and
maps interval-local PTS into the source window. A direct producer-to-consumer
contract test passes without a field adapter. Real acquisition remains absent,
so the diagnostic shell output is not yet promoted to closed evidence.

## Closed continuous-onset acquisition

The v2 runner acquired 59 normalized 4 fps samples over 380–395 seconds with
a 320-pixel gray proxy, absolute frame difference and two FFmpeg threads. The
sample artifact SHA is
`868bee4e9791f96848474ec4c73c71a3018fbfa142611777fea6da7a05e6fde5`.
The first policy replay emitted no candidate because thresholds copied from the
earlier non-gray diagnostic used a different measurement scale; that rejected
artifact is retained externally rather than overwritten.

The benchmark-only, explicitly uncalibrated same-contract policy uses high
0.044 and release 0.035. It emits one review candidate with quiet-baseline max
0.02805, sustained min 0.04509, uncertainty 386.25–386.5 and support
386.5–386.75 seconds. Artifact SHA is
`25596e81094e42f73c81293b551bf7922d61f0970dcbd4f1df3cb5a9a4c0a5a2`.
It still emits no story boundary and authorizes no render.

Five exact four-cardinal composites at 386.0/386.25/386.5/386.75/387.0 were
independently reviewed. They retain the same ski area, lift infrastructure,
slope and nearby skiers; motion, a near object and stitch-band changes explain
the frame-difference burst. Closed evidence therefore records
`no_semantic_change`, not a story transition or pure capture artifact. Evidence
SHA is `a472aff7ca25ed5708d2f1477ee12af8668a26a04fe77dbe3399b1df80fb30d0`.
Temporary review pixels were deleted. The earlier claim that 390 seconds was a
proven late boundary is withdrawn; segment 0000 remains an honest relevance
abstention because its composition changes substantially within the segment.

The deterministic typed-boundary adapter maps this negative observation to
`rejected` with a null effective timestamp and zero authorized boundaries. Its
artifact SHA is
`4d8e7050ebeb535eec1886b933ad17f49e33be90ab8ab53ef48a3ecd15117542`.
No timeline, plan or render is changed.

A typed timeline over the bounded 380–395 acquisition/grid window therefore
contains exactly one 15-second segment with null left/right boundaries. Its SHA
is `63d9473bafed1058df520e9244e85c9144853f4febc05cbff84afa6692b576bb`.
This removes the unsupported 390-second split only inside that bounded window;
it does not claim coverage of 395–415 or modify the legacy timeline.

## Typed planner replay

The typed segment packet samples 383/387.5/392 seconds but no candidate-view
review has been performed, so its closed relevance config abstains. Candidate
utility is consequently neutral and exposes no eligible alternative. The
single-segment continuity evidence and transition utility both contain zero
edges; they do not invent a relationship where no adjacency exists.

The typed global planner retains `context:cardinal:0` for the full 380–395
window with objective, utility, transition utility and planning cost all zero.
It emits no renderer command and is explicitly not production eligible. This
is a successful fail-closed vertical replay, not a directing-quality result;
395–415 remains uncovered and no render is authorized.

External artifact SHA-256 values:

- review packet v2: `6792ed35cbdbb11600195e562bb92197d076aaeb2fdf792790a1b3ff97a7d339`;
- abstain relevance: `37f7bb687be6eea19d5ed6d305c77e2b9e91e919453509943e1a3e68ab7874f2`;
- neutral candidate utility: `e7aa3eb45fd2e986363365c86603b9b45675e75351b1373bdcbbb351051860d4`;
- zero-edge continuity evidence: `02ba0363ec4116540ce48071fd70a19ae02f08cafe624bfb395aae4751d9898b`;
- zero-edge transition utility: `3749672e633af1f4f32270f6a9039db4445632abd9dc155793874b7a0d143277`;
- typed global plan: `29b58c779ad6ae861283da87a669f56ec692cdb510c5205387a28d00a16482a8`.

## Authoritative continuous 380–415 replay

The two diagnostic windows are not merged because doing so would reset onset
hysteresis at 395 seconds. One new 35-second acquisition instead preserves the
continuous state and emits 139 rows. Its only onset is the same byte-for-byte
candidate core at 386.25–386.75; the already reviewed five sample rows are
identical, so the no-semantic-change labels are re-bound to the new lineage.
The complete typed timeline contains one 380–415 segment.

Three transient four-cardinal composites at 387/397.5/408 seconds were reviewed
independently and then deleted. Cardinal 0 is clear, primary and stable;
cardinal 1 is clear, supporting and changing; cardinal 2 is clear, low and
stable; cardinal 3 is partial, low and changing. This is segment composition
evidence, not subject identity or continuous tracking evidence.

Candidate utilities are respectively 3.5, 2.0, 0.5 and -1.0. The typed global
plan therefore retains cardinal 0 for the complete window at objective 3.5,
with no edge, switch or transition cost. Every required evidence scope is
observed, so the plan is production eligible, but it emits no renderer command.
Rendering is skipped because the decision is identical to the existing fixed
cardinal-0 baseline and would provide no new directing evidence.

Authoritative artifact SHA-256 values:

- frame-difference samples: `d6b186c747e594f5a788b152eb3ab773fc887c831e476c121dfbf7bed21bbdb6`;
- onset candidates: `30b2627bc3673f48beedd11d548203fafe5d51a4a02025ccd76413a234ccaa7e`;
- semantic evidence: `ff3c9e1519e6a9ccaad9e580e4da85929c9f93520dbfcfe32cc29a8ce1cdb831`;
- typed boundaries: `d8127140656257cc7dbadad814ad797905a774a55028d5bc0cf18caa4bf289cd`;
- typed timeline: `299bcf9a54a329a13350e6c1ed3953f552a431a6ce493fb12bb01e74c47c7543`;
- observed relevance: `3b6da315a0bc9e338a5ac0a3643651439d7679190b4eb791c3347fb29b14f494`;
- candidate utility: `e7f359ab859af4dbb673ba8a872935b4cbdc5f2b1e2527f494b27dfb9c8b72e3`;
- zero-edge transition utility: `0e4ba4fecc80417d83db722827b18a02ffae05bf5e4a8cf04db208143e085e83`;
- typed global plan: `9c983a0f00a9708e6a594d08f76ac167efa6e03de69c9d1a09bc6a7d3b604de6`.
