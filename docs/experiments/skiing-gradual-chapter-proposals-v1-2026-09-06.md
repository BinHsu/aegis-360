# Skiing gradual chapter proposals v1

Status: blind review complete; proposal policy rejected as chapter detector

## Freeze boundary

The proposal implementation, numeric config and blind protocol were committed
and pushed as `00f9c76` before any real visual-state value, peak or timestamp
was inspected.

- visual-state artifact SHA-256:
  `81c92d89cc51190145e89fd5d02a95c5e480794fa22e0127dafd84b9391b2c91`;
- proposal-policy SHA-256:
  `b0d77819e135f52cecf72ea3519bd868a9554571edb10f68650df044a1e9a1ba`;
- blind-protocol SHA-256:
  `6b8ecfdeff27cc07f22fe984712e51b8c0de122a43ea13ffd4ea71d1da5df7d5`;
- external hidden-key SHA-256:
  `82b0f2cd004734002ecbcc8c0f07a3e2c5183e1d4ef781b84294be4b4a730b5f`.

The hidden key contains only the ordered coarse progression
lift/transport → own skiing/terrain → other skiers and states that exact
transition times are unknown. It was not a proposal input and remains withheld
from reviewers.

## One frozen execution

The committed CLI was executed once. The resulting proposal artifact SHA-256
is `eeddadd92e86478aea79d4659b0ed8edb0fbcc92e74ddc57b7f051a29fa146f3`.
No threshold, window, separation or score rule was changed afterward.

Across 557 eligible centers, the score median and raw MAD are both 0.00335956,
so the pre-data absolute floor fixes the emission threshold at 0.08. Eighteen
local maxima are audited: 15 fall below threshold, two emit, and one is
suppressed by the frozen 45-second separation. No candidate-cap rejection
occurs.

The review-only proposals are:

- proxy second 46, RGB-histogram dominant, persistence-adjusted score
  0.31141222;
- proxy second 297, RGB-histogram dominant, score 0.30437681.

A third qualified maximum at second 337 scores 0.28239276 but is 40 seconds
from the higher-scoring second-297 proposal, so it is rejected exactly as the
frozen policy requires. None of these times is a story boundary yet.

## Deterministic controls

The frozen hash-ordered 10-second lattice resolves controls at proxy seconds
200, 140 and 460, in selection order. They are at least 45 seconds from both
proposals and one another, and at least 30 seconds from all seven previously
reviewed motion-onset hard negatives. No visual-state value, pixel, label or
hidden-key content participates in control selection. Controls are unlabeled
missed-proposal probes, not assumed negative ground truth.

## Next gate

A salted private schedule and exact public neutral projection were generated
once using the separately tested schedule contract. The private schedule SHA
is `7f09f628c30575ddd9934816e2e2af32c219fb2b494ef91d14bccc8d81b81463`;
the public reviewer-index SHA is
`dd26f02b347467628aad92504070fd6399a1f00a8bc753ce3a49a239f7cad0b4`.
The raw salt remains external with owner-only permissions and is not recorded.

Render a standalone transient public bundle whose media references exactly
match the public projection. Reviewers receive only that bundle in fresh
no-history contexts. The current result grants packet rendering only: no
semantic label, typed boundary, candidate selection, production eligibility,
camera command or production render command exists.

## Blind review result

The exact public bundle contains five packets and 30 sanitized 960x540 RGB
PNGs. Its path-independent tree SHA is
`7163a4f54c6daf919a40465dad785050ba0b12061da790b6a33096114c461159`.
Two fresh no-history reviewers independently inspected only the public index
and its declared media. Their five categorical outcomes agree exactly:

- packet 1: `no_semantic_change`;
- packet 2: `story_change`;
- packet 3: `no_semantic_change`;
- packet 4: `no_semantic_change`;
- packet 5: `no_semantic_change`.

Both describe packet 2 as a sustained change from a populated lift/station
area to an open snow slope. Both note ordinary continuous travel in the other
packets and a single-row projection/capture artifact in packet 1.

Only after both reviews were fixed was the coordinator mapping opened. Packet
2 is the second-200 control. Packets 1 and 4 are the second-297 and second-46
proposals respectively; packets 3 and 5 are controls at seconds 140 and 460.
Thus both emitted proposals are observed negatives while one of three
unlabeled controls exposes a miss. The hidden key confirms only the coarse
ordered progression lift/transport → own skiing/terrain → other skiers and
explicitly contains no exact transition time.

This is a bounded rejection, not a calibrated precision/recall estimate. The
policy must not be threshold-tuned on this result or promoted to typed-boundary
authority. Next, inspect why the persistent visual descriptors favor 46/297
over 200 and design a new precommitted signal hypothesis on separate evidence.

## Causal numeric audit

The artifact hashes were reverified before a read-only numeric audit. The
failure is a representation/target mismatch plus a fixed-window limitation,
not faulty score arithmetic or local-maximum selection.

- At 46, RGB state distance 0.38828487 minus dispersions 0.04049841 and
  0.03637424 leaves 0.31141222. All eight luma tiles darken and roughly
  0.25–0.33 histogram mass per channel moves out of the highest bin.
- At 200, RGB distance is only 0.06026114; dispersions 0.01090838 and
  0.02633608 leave 0.02301667. Spatial distance 0.03934794 is entirely
  cancelled by 0.04244326 dispersion. It is a local maximum, so local-peak and
  separation logic did not miss it; the coarse snow-dominated states look
  similar while the later window is internally variable.
- At 297, RGB distance 0.37530744 minus dispersion leaves 0.30437681, driven by
  about 0.30 mass per channel moving into the highest bin.
- At 337, the reciprocal RGB shift leaves 0.28239276. The 297 after-window and
  337 before-window are both [307,327), proving entry and exit around one
  roughly 40-second visual excursion. Separation hides the second peak but
  does not model return to an earlier state.

The proposal scorer does not consume the feature artifact's five/15-second
`long_baseline_change`; this matches the frozen contract. Simply wiring it is
not supported as a remedy: mean 15-second RGB change near 46/200/297/337 is
0.1951/0.0456/0.0861/0.3536 and still favors appearance excursions.

A falsifiable successor hypothesis is pre-design only: color-independent
tilewise edge-density and gradient-orientation occupancy, plus an explicit
A→B→A episode audit, should rank persistent layout/context changes above
palette-only travel excursions. It must be frozen before and tested on separate
human-labeled evidence. It is rejected if held-out semantic changes do not
improve relative to continuous-travel/color negatives, or if short valid
chapters are systematically collapsed.
