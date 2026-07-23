# Spherical stabilization and segment policy

Status: Proposed design; interfaces and defaults are unvalidated

## Purpose and authority

This document proposes a camera-agnostic stabilization boundary for
monoscopic equirectangular (ERP) sources that do not carry usable gyro
metadata. It also separates editorial segment value from viewing comfort so
that action footage is not rejected merely because it contains intentional
motion.

The proposal follows ADR 0001, ADR 0002, ADR 0005 and ADR 0006. In particular:

- stabilization is offline and operates on the normalized spherical input;
- analysis artifacts are reusable and source-resolution rendering remains a
  single streaming pass;
- **Full Story** preserves chronology and most source duration;
- camera-motion costs do not replace explainable editorial planning.

This is not an accepted ADR. Parameter values, comfort thresholds and the
visual motion estimator all require synthetic and benchmark evidence.

## Known facts, observed evidence and hypotheses

### Known project contracts

- The POC input boundary is a validated monoscopic ERP stream.
- Internal angles use radians and the coordinate conventions in
  `spherical-geometry.md`.
- Rendering consumes one selected camera path and must not silently change
  editorial decisions.
- The decision trace must record configuration, fallbacks, missing evidence
  and rejected alternatives without absolute source paths.
- The current public WebM benchmarks do not provide a project-validated native
  gyro path.

### Observed repository evidence

- The rejected 110/120-degree comparison did not materially improve the
  owner's motion-sickness judgment.
- The fixed-forward and auto-directed tail windows had similar large
  translation-proxy steps, which is evidence that source/global motion is an
  important contributor. The proxy cannot isolate roll, parallax or
  perspective rotation.
- Direct ERP measurement found substantial motion in the original Old Ghost
  Road source before flat reprojection.
- The first flat post-warp attempt worsened the measured median step and p95
  vector change. It is negative evidence for that implementation, not proof
  that all residual post-warp stabilization is ineffective.

### Unverified hypotheses

- Robust multi-view visual registration can recover a useful global rotation
  path from these gyro-free ERP sources.
- Most uncomfortable source motion can be reduced by smoothing a rig
  orientation on the sphere while retaining slower intentional lean and turn.
- An `action-natural` policy will be preferred to full horizon lock for the
  first-person benchmarks.
- A single spherical composition of stabilization and directing will avoid
  the resampling and conflicting-motion problems of sequential spherical
  reframe followed by primary flat stabilization.

## Coordinate and transform contract

All orientations are unit quaternions representing active right-handed
rotations. Quaternion multiplication order and the conversion to a renderer
must be locked by synthetic tests before a real render. The names below define
semantics; they do not assume FFmpeg, Core Image or Metal matrix conventions.

At source time `t`:

- `R(t)` is the estimated raw rig orientation, mapping an ERP/source-local ray
  into a stable reference-world frame.
- `S(t)` is the desired stabilized rig orientation in the same mapping and
  reference frame. It is derived from `R(t)`, mode parameters and estimator
  confidence.
- `D(t)` is the editorial virtual-camera orientation relative to the
  stabilized rig frame. It includes the selected yaw, pitch and roll; FOV is
  carried separately.
- `P(t)` is the orientation with which the renderer samples the raw ERP for
  the output camera.

The canonical composition is:

```text
C(t) = inverse(R(t)) * S(t)
P(t) = C(t) * D(t)
```

`C(t)` is the source stabilization correction. The render pass applies
`P(t)` once while projecting from the original ERP to the output
rectilinear frame.

The following identities are required fixtures:

- no stabilization: `S(t) = R(t)`, therefore `C(t) = identity` and
  `P(t) = D(t)`;
- fixed stabilized view: `D(t) = identity`, therefore the output follows only
  the stabilized rig;
- static source: constant `R(t)` must not acquire compensating motion;
- seam-crossing rotations must take the short path;
- a known injected roll must be cancelled with the validated sign and order.

Candidate directions detected in raw ERP coordinates must not be inserted
directly into `D(t)`. A raw candidate ray is first transported into the
stabilized rig frame:

```text
candidate_stable(t) = inverse(S(t)) * R(t) * candidate_raw(t)
```

Planning, interpolation and transition costs operate on this stabilized
candidate representation. This prevents the director from chasing vibration
that stabilization is intended to remove.

## Gyro-free source path `R(t)`

### Proposed estimator

1. Decode a timestamp-preserving, bounded-resolution ERP proxy.
2. Project each analysis sample into overlapping cubemap faces or validated
   rectilinear viewports. Do not track directly across distorted ERP poles.
3. Match static-scene features between adjacent samples. Mark observations on
   moving people, bicycles, vehicles and low-confidence regions as possible
   outliers when masks or tracks are available.
4. Robustly fit one global `SO(3)` rotation to spherical ray
   correspondences. Record inlier coverage by face and angular distribution,
   not only an aggregate residual.
5. Chain adjacent rotations into `R(t)` and periodically perform bounded
   window optimization to reduce drift without retaining the whole video in
   memory.
6. Emit confidence and explicit failure reasons for every interval. Do not
   invent a high-confidence rotation across insufficient texture, severe
   blur, stitching failure or foreground-dominated motion.

Visual rotation cannot fully model translation parallax, rolling shutter,
stitching errors or object motion. Residual non-rotational motion is therefore
diagnostic evidence and may force a wider fallback or segment-quality
decision; it must not be absorbed into an arbitrarily moving spherical
camera.

### Source-motion artifact

The analysis pass should persist a compact, renderer-independent artifact:

```json
{
  "schema_version": "aegis360.source-motion.v1",
  "source_id": "privacy-safe-id",
  "coordinate_convention": "aegis360-spherical-v1",
  "estimator": {
    "backend": "visual-multiview-so3",
    "proxy": {"width": 0, "height": 0, "sample_fps": 0},
    "config_id": "versioned-config-id"
  },
  "samples": [
    {
      "pts_seconds": 0,
      "raw_orientation_xyzw": [0, 0, 0, 1],
      "confidence": 0,
      "inlier_ratio": 0,
      "face_coverage": 0,
      "residual_radians": 0,
      "state": "measured"
    }
  ],
  "gaps": []
}
```

Allowed sample states are `measured`, `interpolated`, `held` and `invalid`.
Interpolation and hold durations are bounded configuration values and are
visible in the trace.

## Stabilized source path `S(t)`

`S(t)` is optimized in quaternion/rotation space, not by independently
low-pass filtering wrapped yaw, pitch and roll. The objective should expose:

- fidelity to `R(t)`;
- angular velocity, acceleration and jerk penalties;
- a roll/horizon penalty;
- a bounded correction-angle penalty;
- confidence-weighted trust in measured samples;
- boundary and gap behavior.

Cuts or discontinuities in `D(t)` do not reset `S(t)`: source motion is an
independent physical estimate. Conversely, an estimator gap must not force an
editorial cut. The planner receives the gap and chooses among hold,
fallback-wide, a cut to another valid view, or a later Highlights-only time
edit.

The optimizer may use future samples because runtime is offline. It must
produce a timestamped path that the render pass can interpolate at every
source PTS. A lightweight final flat residual correction may be evaluated
later, but it is not part of the primary stabilization contract and cannot
silently alter `P(t)`.

## Stabilization modes

The modes are named policies over the same parameters. The ranges below are
starting hypotheses for proxy experiments, not accepted comfort thresholds.

| Parameter | `cinematic` | `action-natural` | `fpv` |
| --- | ---: | ---: | ---: |
| orientation smoothing horizon | 1.0–2.0 s | 0.35–0.75 s | 0.15–0.35 s |
| roll/horizon correction strength | 0.9–1.0 | 0.55–0.8 | 0.15–0.4 |
| retained low-frequency lean | 0–10% | 35–65% | 70–100% |
| high-frequency vibration rejection | strong | strong | medium–strong |
| maximum correction angle | 35–60° | 20–40° | 10–25° |
| correction recovery | slow | medium | fast |
| minimum default output HFOV | 90° | 105° | 115° |

Every mode config must explicitly provide:

```text
smoothing_horizon_seconds
orientation_fidelity_weight
angular_velocity_weight
angular_acceleration_weight
angular_jerk_weight
horizon_roll_weight
lean_retention
max_correction_radians
max_correction_velocity_radians_per_second
max_gap_interpolation_seconds
min_estimator_confidence
default_hfov_radians
fallback_hfov_radians
max_dynamic_fov_rate_radians_per_second
```

`action-natural` is the proposed first benchmark default because the target is
an ordinary viewer of first-person action footage: reject repetitive
high-frequency vibration while retaining bounded turn and landing character.
This choice remains a hypothesis until blinded comparison.

Dynamic FOV is a coverage and comfort control, not a substitute for a valid
motion path. Zoom changes are rate-limited and recorded. The renderer must
prove that the chosen FOV has source coverage and no blank projection regions.

## Segment value and treatment policy

Editorial value and technical comfort are scored independently over bounded
candidate intervals:

```text
editorial_value =
    event_interest
  + subject_or_context_readability
  + novelty
  + continuity_value

technical_risk =
    residual_high_frequency_motion
  + horizon_instability
  + estimator_uncertainty
  + blur_or_occlusion
  + stitch_or_projection_defect
  + correction_or_crop_cost
```

Raw motion magnitude is neither an event score nor an automatic rejection
signal. Intent evidence may include coherent low-frequency turn/lean,
agreement with travel direction, a visible jump/landing/impact, and consistent
scene flow. These are named evidence terms rather than a binary claim that
the system knows the camera operator's intent.

Each interval receives exactly one proposed treatment:

| Treatment | Meaning | Full Story behavior | Highlights behavior |
| --- | --- | --- | --- |
| `KEEP_RAW` | Valuable and already comfortable; retain natural motion | Set `S=R` for the interval, with bounded transitions at its boundaries | Same |
| `KEEP_SOFTENED` | Valuable; suppress unwanted motion with the selected mode | Apply `S(t)` | Same |
| `KEEP_SHORT` | Valuable core event but surrounding duration has high technical risk or repetition | Recommendation only: retain duration and use `KEEP_SOFTENED` or `FALLBACK_WIDE`; do not shorten chronology | May retain only the scored event core plus configured handles |
| `FALLBACK_WIDE` | Direction or correction is unreliable but the interval remains watchable in context | Use a stable forward/context candidate and wider rate-limited FOV | Same, if preferable to shortening |
| `SKIP` | No acceptable view remains, or the interval is editorially dominated by a better alternative | No ordinary quality-based deletion. Mark as `skip_recommended` and use the least-risk fallback. Decode corruption follows explicit media-recovery policy and preserves timing where possible | May remove the interval subject to continuity and event-coverage constraints |

This mapping is required by ADR 0002. `KEEP_SHORT` and `SKIP` must not become
implicit Highlights behavior inside the Full Story planner.

### Proposed decision order

1. Reject invalid estimator evidence; do not score fabricated motion.
2. Determine whether at least one candidate view is technically renderable.
3. Score editorial value independently of technical risk.
4. If value is high, prefer `KEEP_RAW` for intentional, already comfortable
   motion or `KEEP_SOFTENED` when stabilization reduces predicted risk.
5. If directing confidence is low but context remains usable, choose
   `FALLBACK_WIDE`.
6. Emit `KEEP_SHORT` when a valuable core is bounded by poor/repetitive
   material; only Highlights may enact the trim.
7. Emit `SKIP` only when no acceptable view remains or value is dominated.
   Full Story records but does not ordinarily enact it.

Thresholds are versioned configuration, not literals in the scorer. At
minimum, traces retain the raw/normalized terms, threshold comparisons,
selected treatment, mode, fallback and the result of evaluating alternatives.

## Planner and renderer interfaces

The planner consumes stabilized candidate directions, source-motion
confidence, segment treatments and FOV feasibility. It emits separate
artifacts:

- `source_stabilization_path`: timestamped `R(t)`, `S(t)`, confidence, mode
  and gap/fallback state;
- `director_path`: timestamped `D(t)`, FOV, selected candidate, transition or
  cut, and treatment;
- `composed_render_path`: timestamped `P(t)`, FOV and provenance linking both
  inputs.

The composed artifact is deterministic for fixed inputs and config. It is a
cacheable plan, not rendered media. The renderer:

1. validates matching source identity, timebase, coordinate schema and path
   coverage;
2. interpolates `R`, `S` and `D` at each source PTS using the declared method;
3. computes `P = inverse(R) * S * D`;
4. performs one source ERP-to-rectilinear projection;
5. preserves audio and timestamps and records any explicit recovery;
6. never derives a new stabilization or editorial path.

Composition should occur from the component paths at render PTS rather than
interpolating sparsely pre-composed Euler angles. `composed_render_path`
therefore stores component provenance and may contain dense verified
quaternions for adapters that require them.

## Failure behavior

- Insufficient visual coverage: hold only for the configured duration, then
  reduce correction toward identity and request `FALLBACK_WIDE`.
- Foreground-dominated or parallax-heavy fit: lower confidence; do not treat
  the moving subject as global rig rotation.
- Abrupt confidence recovery: rate-limit correction re-entry to avoid a snap.
- Correction exceeds configured angle/velocity or feasible coverage: clamp
  only with an explicit warning and prefer fallback; never hide the clamp.
- Missing path at a source PTS, coordinate mismatch or non-finite quaternion:
  fail closed before source-resolution render.

## Evidence gates

No benchmark review candidate should be rendered from this design until:

1. Known yaw, pitch and roll synthetic fixtures establish quaternion order,
   signs, interpolation and single-projection output.
2. A synthetic ERP with known rig shake demonstrates that `S(t)` reduces the
   injected high-frequency motion without erasing a known slow intentional
   turn.
3. Confidence-gap fixtures demonstrate bounded hold, recovery and
   `FALLBACK_WIDE` without a correction snap.
4. `KEEP_SHORT` and `SKIP` tests prove that Full Story duration is not
   silently shortened.
5. Proxy A/B/C artifacts compare no stabilization, `cinematic` and
   `action-natural` on the same timestamps before any new full-resolution
   30-second candidate.
6. Objective motion, horizon, crop/FOV and path-derivative evidence is reported
   alongside blinded human comfort and motion-character preference. No single
   metric is accepted as comfort ground truth.

