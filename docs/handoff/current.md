# Current handoff

Updated: 2026-09-06T10:05:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: de10b29
Remote status: `origin/main` at `de10b29` before this checkpoint
Working tree at checkpoint: complete 380–415 replay, zero-candidate CLI and typed review-runner wiring

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless
MacBook Air M4 with 16 GB unified memory. The current gate is scaling the typed
continuous-onset route beyond one bounded Skiing interval without creating
review or render work unsupported by evidence.

## Last completed milestone

The previous pushed commit `de10b29` completed typed packet/relevance,
zero-edge causal continuity and strict numeric global-planner integration. This
checkpoint extends the real evidence window from 380–395 to a continuous
380–415 acquisition and closes observed segment-view relevance.

The frame-difference runner emits 139 normalized rows. The frozen uncalibrated
policy finds only the prior 386.25–386.75 motion burst. Its five semantic rows
are byte-identical to the independently reviewed bounded packet core, so
`no_semantic_change` is re-bound to the new source/window lineage. Zero typed
boundaries produce one complete 35-second segment.

Typed packet v2 schedules 387/397.5/408-second four-cardinal composites. Main
and independent agent review agree cardinal 0 is clear/primary/stable. The
other candidates are lower-value or changing. Utility scores are c0=3.5,
c1=2.0, c2=0.5, c3=-1.0. The plan retains c0 with no edge, switch or cost and
objective 3.5. It is production eligible but emits no renderer command.

No video was rendered: the selected view is identical to the existing fixed
cardinal-0 baseline, so another file would add no directing evidence. All
transient review pixels were deleted.

Two vertical CLI gaps were closed:

- zero-onset windows may call the typed-boundary CLI with no packet/evidence
  flags; both lists still must have equal length;
- transient story review explicitly accepts packet v2 at both runner and
  render-job layers, retains exactly three composites and mandatory cleanup.

## Repository state

- Expected branch: `main`; baseline/remote before checkpoint: `de10b29`.
- Dirty files should be only the CLI/review wiring, tests and current docs.
- External evidence is untracked under the configured data root.

## Verified

- The authoritative 380–415 plan SHA is
  `9c983a0f00a9708e6a594d08f76ac167efa6e03de69c9d1a09bc6a7d3b604de6`.
- The authoritative typed timeline SHA is
  `299bcf9a54a329a13350e6c1ed3953f552a431a6ce493fb12bb01e74c47c7543`.
- Packet/job and zero-candidate targeted tests pass.
- Full suite: 498 tests pass; handoff checker and diff check pass.
- No temporary review pixels remain.

## Rejected

- Do not merge independently classified 380–395 and 395–415 windows: that
  resets hysteresis and treats the join as an implicit semantic boundary.
- The legacy hand-authored 390-second split is pilot edit timing, not source
  story-boundary evidence.
- The 386-second motion burst is not a story change.
- A production-eligible plan does not require a redundant render when its
  decision is identical to an already validated baseline.
- Segment composition evidence does not prove subject identity or tracking.

## Pending

- Run full-source Skiing frame-difference acquisition under the same v2 config
  and measure onset count before expanding semantic review.
- Keep one continuous hysteresis state across the source.
- Review only emitted sparse onset packets and resulting typed segments.
- Render only if a complete observed plan materially differs from an existing
  validated baseline.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After pushing, run `scripts/run_ffmpeg_frame_difference.py` on the full
616.392-second Skiing source with
`config/skiing-continuous-onset-acquisition-v2.json`. Store output externally,
then run `scripts/build_continuous_onset_candidates.py` with the frozen Skiing
policy. Stop expansion only if the sparse review count itself creates a real
cost/quality decision.

## External artifacts

Set `AEGIS_DATA_DIR` locally. Authoritative artifacts are under
`outputs/continuous-onset/skiing-t380-t415-v1/`. Exact hashes are recorded in
`docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`. The separate
`skiing-t395-t415-v1` directory is diagnostic only. Never commit either.

## Active agents

No delegated work remains active. The independent visual review completed
without editing repository files.

## Safety and claims

- Never commit media, frames, audio, model weights, identity embeddings or
  absolute local source paths.
- Analysis/rendering remain offline; downloads require explicit authority.
- Keep queues and memory bounded for the 16 GB unified-memory machine.
- Geometry, faces and mouth motion do not establish identity or speech.
- Policy v1 uses destination-segment duration as dwell and applies minimum
  advantage before transition costs; do not silently change these semantics.
- Git history is the archive; status and handoff contain current state only.
- Stop only for a real user decision, new authority or external dependency.
