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
