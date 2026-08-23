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

The matrix is not yet consumed by global story DP and authorizes no render.
Next is exact planner integration plus an ablation showing that removing this
component erases the expected baseline advantage.
