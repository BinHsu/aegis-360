# Current handoff

Updated: 2026-08-02T17:05:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 4831c10
Remote status: `origin/main` contains the baseline commit
Working tree at checkpoint: only this checkpoint metadata differs from baseline

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The current objective is continuous multi-view semantic acquisition
that can prefer sustained non-ego people/riders over near-field equipment.

## Last completed milestone

The new planning-only orchestrator merges independent semantic lifecycles,
keeps forward context unique, rejects duplicate IDs, removes terminated tracks
and emits path-free atomic artifacts without invoking a renderer. It also
evaluates decisions in the actual static-shot representation.

The bounded Old Ghost Road 60–68 second bicycle replay uses the unchanged
`greedy-first-slice-v1.toml`. It selects the lifecycle bicycle for 23/32
decisions and forward context for 9/32, falling back exactly at termination.
The bicycle shot lasts 5.75 seconds at about yaw 15.89 degrees and pitch
-34.03 degrees, with a 37.14-degree maximum effective difference from fixed.
This passes the pose floor. Its v4 fixed/auto/debug render also passes equal-
encoder and mechanical checks, but paired-frame inspection rejects it: the
selected lower bicycle region is likely the wearer's own bicycle/near-field
equipment and is not a compelling ordinary-viewer subject.

An independent 105–113 second person diagnostic stays forward for all 32
decisions. The person utility exceeds forward, but its active lifecycle lasts
only 0.25 seconds and correctly cannot satisfy the unchanged 0.5-second
challenger hold before grace/termination.

The milestone also fixed a renderer-contract false positive: forward context
is already a viewport, so framing safety no longer adds subject padding to it.
An all-forward plan now correctly fails differentiation.

## Repository state

- Expected branch: `main`.
- Baseline commit `4831c10` is present on `origin/main`.
- Commit `4831c10` is intentionally unsigned because the host SSH signing key
  required an unavailable interactive passphrase; global Git settings were not
  changed.
- Benchmark media, model weights and generated artifacts are external and
  gitignored.
- Current documentation edits intentionally replace superseded status and
  handoff timelines; Git history remains their only archive.

## Verified

- `python3 -m unittest discover -s tests -v`: 233 tests passed.
- `python3 scripts/check_handoff.py`: passed with current-only size/history
  enforcement active.
- FFmpeg geometry and renderer convention gates have synthetic evidence.
- YOLOX-Tiny FLOAT32 Core ML conversion and decoded outputs pass the frozen
  equivalence protocol.
- The load-once detector stream exceeds the required 4 fps cadence with ample
  memory headroom on the reference machine.
- Detector refresh, grace, termination, post-terminal rejection, fresh-ID
  acquisition proposal and lifecycle-to-planner fallback have unit and bounded
  real-sequence evidence.
- Multi-lifecycle merge, atomic/path-free planning output, overwrite refusal
  and renderer-aware pose differentiation have synthetic contracts.
- The corrected group-policy comparison selects forward 32/32 and fails the
  pose gate. The unchanged semantic policy selects bicycle 23/32 and passes.
- Equal-contract v4 rendering passes mechanically and is rejected visually
  before owner review. The person diagnostic correctly fails differentiation.

## Rejected

- Do not claim that any rendered auto-directed candidate has passed owner
  review.
- Do not widen rectilinear FOV again as the primary shake remedy.
- Do not tune gyro-free stabilization thresholds again for this POC. The
  causal, masked and tiled variants did not beat fixed-forward on the bounded
  render proxy; raw/fixed treatment is retained.
- Do not use generic saliency geometry as identity or editorial persistence.
- Do not lower the accepted greedy switch margin merely to manufacture visual
  differences.
- Do not ask the owner to review media until the renderer-aware pre-review gate
  and representative paired-frame inspection both pass.
- Do not use the rejected semantic-planning `v1` artifact; its pose result
  predates the forward-context FOV correction.
- Do not send the bicycle v4 render to the owner; visible differentiation is
  real but the chosen lower/near-field subject is not useful.
- Do not lower challenger hold to force the short person lifecycle to switch.

## Pending

- Define a privacy-safe, versioned multi-view detector-event artifact that
  preserves accepted person/bicycle boxes, viewport poses and timestamps but
  no pixels or paths.
- Add a synthetic contract for continuous acquisition/lifecycle orchestration
  across several fresh candidates without reusing terminated IDs.
- Run a bounded 30-second Old Ghost Road analysis across overlapping
  viewports. Preserve the existing hold/margin settings and do not render
  unless a sustained candidate survives agent semantic inspection.
- The explainable global planner, richer event/novelty/audio interest signals,
  seam handoff and verified identity remain later work.

## Next commands

Run from the repository root. Confirm the checkpoint, then inspect the
existing detector stream and acquisition contracts before defining the
multi-view event artifact:

```sh
git status --short --branch
git log -1 --oneline
python3 scripts/check_handoff.py
python3 -m unittest discover -s tests -v
sed -n '1,260p' scripts/benchmark_yolox_coreml_stream.py
sed -n '1,260p' src/aegis360/new_track_acquisition.py
sed -n '1,260p' src/aegis360/refresh_lifecycle.py
```

The next artifact contract must be fake/synthetic-tested before benchmark use,
must be path-free and must refuse overwrite. Do not tune scoring from the two
diagnostic clips.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. Relevant immutable
evidence beneath it includes:

- `outputs/yolox-stream-benchmark/old-ghost-road-t0-180-yaw0-4fps-numpy-v1/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t60-yaw0-bicycle-8s-4fps-v3/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t105-yawm90-person-8s-4fps-v4/`
- `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v2/`
- `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v3/`
- `outputs/semantic-planning/old-ghost-road-t60-bicycle-8s-v4-render-ready/`
- `outputs/semantic-planning/old-ghost-road-t105-person-8s-v1/`
- `outputs/auto-directed/old-ghost-road-30s-v1/bundle-v8-group-coverage-render/`
- `outputs/source-motion/old-ghost-road-40-45-causal-comparison-v1/`
- `outputs/source-motion/old-ghost-road-45-50-causal-heldout-v1/`

Do not overwrite these directories. Do not commit their contents.

## Active agents

No delegated work is active or required to resume this checkpoint.

## Safety and claims

- Do not commit source media, generated video, extracted frames, model weights,
  faces, audio, absolute paths or identity data.
- Setup and acquisition require explicit network action; analysis and rendering
  remain offline.
- Preserve bounded queues and the 16 GB unified-memory constraint.
- Treat semantic/geometry continuity as nonidentity unless a stronger adapter
  explicitly proves otherwise.
- Do not claim stabilization, comfort, directing quality, real-time execution
  or thermal stability beyond the recorded experiment boundaries.
