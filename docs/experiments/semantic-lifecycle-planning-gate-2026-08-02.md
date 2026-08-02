# Semantic lifecycle planning gate — 2026-08-02

Status: Integration passed; first bounded render rejected before owner review

## Question

Can independently bounded semantic lifecycles be merged into one candidate
timeline, removed exactly at termination, passed through the unchanged greedy
planner and evaluated in the actual static-shot representation before video is
rendered?

## Contract

`src/aegis360/semantic_sequence.py` merges lifecycle candidate sequences by
timestamp. Each lifecycle keeps its fresh track ID, forward context appears
exactly once per timestamp, duplicate IDs fail closed and a terminated track
cannot contribute later candidates.

`scripts/plan_semantic_lifecycle_sequence.py` consumes a local manifest,
versioned greedy config and new output directory. It emits only `trace.json`
and `planning-gate.json`, refuses overwrite, calls no renderer and removes
input paths from its output. The gate converts decisions through
`greedy_trace_to_static_shots` and applies the existing 8-degree, two-second
perceptibility floor.

Synthetic tests cover overlapping lifecycles, independent termination,
duplicate-ID rejection, empty-input rejection, path-free atomic output and
overwrite refusal.

## Renderer-contract correction

The first real smoke exposed a pre-existing false positive. Framing safety
treated `context:forward` horizontal FOV as a subject extent and added ten
degrees of padding on each side. An all-forward plan therefore appeared to
differ from the fixed 110-degree peer by 20 degrees.

`greedy_trace_to_static_shots` now retains candidate type and treats forward
context as the already-selected fixed viewport. It still applies padding to
subject/group extents. A regression test requires an all-forward 110-degree
plan to remain 110 degrees after framing safety.

## Real planning-only evidence

The bounded input reuses the immutable Old Ghost Road 60–68 second bicycle
Vision track and YOLOX refresh lifecycle. It does not rerun or reinterpret
detector identity. Source and model facts remain those recorded in
`coreml-seeded-vision-tracking-2026-07-29.md` and
`yolox-tiny-conversion-equivalence-protocol.md`.

Two corrected comparisons were run without changing hysteresis:

| Config | Bicycle decisions | Forward decisions | Pose gate | Interpretation |
| --- | ---: | ---: | --- | --- |
| `greedy-group-context-v1.toml` | 0/32 | 32/32 | fail | Group ablation diverts presence weight and is not the semantic policy |
| `greedy-first-slice-v1.toml` | 23/32 | 9/32 | pass | Existing semantic presence weight selects the bounded lifecycle |

Under the semantic config, the static renderer representation has two shots.
The bicycle shot spans 0–5.75 seconds at approximately yaw 15.89 degrees,
pitch -34.03 degrees and 130-degree horizontal FOV. The lifecycle terminates
at source time 65.75 seconds; the plan immediately falls back to forward for
the remaining 2.25 seconds. The bicycle shot has 37.14 degrees maximum
effective difference from fixed and contributes all 5.75 distinct seconds.

External artifacts under `AEGIS_DATA_DIR`:

- Rejected corrected group-policy run:
  `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v2/`
- Accepted semantic-policy run:
  `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v3/`
- Render-ready replay and equal-encoder internal render:
  `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v4-render-ready/`
- Independent person planning diagnostic:
  `outputs/semantic-planning/old-ghost-road-t105-person-8s-v1/`

The earlier `v1` artifact is rejected because it predates the forward-context
FOV correction and contains the false-positive result.

## Internal render and visual inspection

The v4 planning replay emits the same 23 bicycle and nine forward decisions as
v3 plus render-ready config and camera-path documents. Fixed and auto outputs
are both 1920x1080 H.264 High, yuv420p at 25 fps under libx264 fast/CRF 18.
The mechanical pre-review gate passes.

Paired frames at relative 1, 4, 6 and 7 seconds reject the candidate before
owner review. The auto shot is visibly different and technically clear, but at
one second it primarily frames gravel and the lower bicycle region; at four
seconds nearby cyclists enter the view. Trace pose varies by only about one to
two degrees, so this is not a static-shot tracking failure. The detector and
planner are consistently favoring a lower-frame bicycle region that is likely
the camera wearer's own bicycle or near-field equipment. Semantic class alone
does not make it an interesting subject.

The independent person diagnostic supplies the complementary failure. A
person lifecycle at source time 108.0/108.25 has utility about 0.54 versus
forward's 0.35, but remains active for only 0.25 seconds. It cannot satisfy the
unchanged 0.5-second challenger hold before grace and termination, so the plan
correctly stays forward for all 32 decisions and fails the pose gate.

These two observations do not justify lowering hysteresis or adding a fitted
bottom-of-frame penalty. They require broader continuous semantic coverage so
other people/riders can form lifecycles long enough to compete with ego
equipment and forward context.

## Verification

- `python3 -m unittest discover -s tests -v`: 233 tests passed.
- `python3 scripts/check_handoff.py`: passed.
- Shell syntax checks: passed.
- Equal-contract v4 render and mechanical pre-review gate: passed.
- Agent paired-frame visual gate: rejected; no owner review requested.

## Limitations and next gate

This result reuses one previously bounded lifecycle and proves orchestration,
termination and visible pose differentiation only. It does not establish
identity, semantic interest, comfort, image quality, continuous 30-second
detection/tracking or a successful auto-directed video.

Next extend acquisition/lifecycle orchestration to a continuous, multi-view
30-second semantic interval. Preserve the existing hold/margin settings and
record whether non-ego people or bicycles produce sustained candidates before
another render.
