# Current handoff

Updated: 2026-08-02T16:20:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 972e666
Remote status: `main` matches `origin/main` at the baseline commit
Working tree at checkpoint: documentation cleanup in progress

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer. The current objective is a bounded planning-only semantic integration
that can produce materially differentiated renderer-visible shots before
another owner video review.

## Last completed milestone

The detector path is fast enough for the POC on the reference M4 MacBook Air.
The load-once YOLOX-Tiny FLOAT32 Core ML stream analyzed a 180-second Old Ghost
Road source workload at 4 fps: 720 frames completed in 15.680 seconds at 45.92
fps with 383,926,272-byte peak RSS. The run preserved the frozen decoder
contract and used path-free external artifacts. Because the computation lasted
only 15.7 wall seconds, it is bounded-completion evidence rather than a
thermal-duration result.

The preceding directing milestone established a conservative semantic
lifecycle. A confirmed bicycle seed can drive Vision tracking and compatible
YOLOX refreshes; bounded misses enter grace and then terminate the candidate.
Post-terminal observations cannot revive the old track. Planner integration
removes it at termination and falls back to forward context. Geometry never
claims verified identity or editorial persistence.

## Repository state

- Expected branch: `main`.
- Baseline and remote head: `972e666`.
- Baseline working tree was clean and synchronized with `origin/main`.
- Benchmark media, model weights and generated artifacts are external and
  gitignored.
- Current documentation edits intentionally replace superseded status and
  handoff timelines; Git history remains their only archive.

## Verified

- `python3 -m unittest discover -s tests -v`: 228 tests passed.
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

## Pending

- Connect the existing load-once semantic detector output to detector refresh,
  Vision lifecycle, lifecycle candidates and the greedy planner over one
  longer bounded benchmark interval.
- Persist a planning-only, path-free decision trace with semantic/lifecycle
  provenance and explicit gaps.
- Replay the actual static-shot renderer representation and require sustained
  pose separation from fixed-forward before rendering.
- If differentiation is insufficient, improve candidate coverage or interest
  evidence. Do not render and do not return to stabilization tuning.
- After a differentiated planning gate passes, render fixed/auto/debug peers
  under the same encoder contract and run mechanical plus visual pre-review.
- The explainable global planner, richer event/novelty/audio interest signals,
  seam handoff and verified identity remain later work.

## Next commands

Run from the repository root. First confirm the checkpoint, then inspect the
three existing integration boundaries that the next bounded runner must join:

```sh
git status --short --branch
git log -1 --oneline
python3 scripts/check_handoff.py
python3 -m unittest discover -s tests -v
rg -n "def main|class |schema|lifecycle|decision" \
  scripts/benchmark_yolox_coreml_stream.py \
  scripts/run_yolox_refresh_sequence.py \
  scripts/plan_lifecycle_diagnostic.py \
  src/aegis360/lifecycle_candidates.py
```

The next implementation must add a synthetic/fake orchestration contract
before using benchmark media. It must remain planning-only and must refuse to
overwrite an existing external artifact directory.

## External artifacts

The artifact root is configured by `AEGIS_DATA_DIR`. Relevant immutable
evidence beneath it includes:

- `outputs/yolox-stream-benchmark/old-ghost-road-t0-180-yaw0-4fps-numpy-v1/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t60-yaw0-bicycle-8s-4fps-v3/`
- `outputs/yolox-refresh-sequence/old-ghost-road-t105-yawm90-person-8s-4fps-v4/`
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
