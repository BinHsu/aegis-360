# Skiing gradual chapter proposals v1

Status: frozen proposal run complete; semantic review not started

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

Create a salted private schedule and an exact public neutral projection using
the separately tested schedule contract. Freeze both artifact hashes before
rendering. Reviewers receive only the standalone public bundle in fresh
no-history contexts. The current result grants review scheduling only: no
semantic label, typed boundary, candidate selection, production eligibility,
camera command or render command exists.
