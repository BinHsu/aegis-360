# Current handoff

Updated: 2026-09-06T10:45:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: ad1508b
Remote status: `origin/main` at `ad1508b` before this checkpoint
Working tree at checkpoint: full-source negative evidence, dedicated transient onset runner and current docs

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The next gate is a low-cost source of
gradual story/activity chapter proposals; frame-difference onset remains only a
motion-peak/corroboration signal.

## Last completed milestone

Commit `ad1508b` completed a production-eligible 380–415 Skiing typed replay.
It correctly retains cardinal 0 and skips a redundant fixed-forward render.

This checkpoint runs the identical acquisition contract over the complete
616.392-second source. It emits 2,465 normalized rows; the frozen uncalibrated
policy reduces 415 above-high rows to seven sustained candidates at 76.75,
327.25, 386.5, 429.75, 499.75, 506.25 and 565.25 seconds.

A new dedicated transient runner exact-validates onset/samples/grid/packet,
renders at most five silent 2x2 cardinal composites, passes a path-free index
to an argv adapter, and deletes its temporary directory after success or
failure. All seven onset packets were reviewed with no retained pixels.

Independent reviews agree: six candidates are `no_semantic_change`; 327.25 is
a stitch/stretch `capture_artifact`. The 506.25 TRAILS CROSSING sign is real
foreground parallax, not a chapter start. Typed boundaries authorize zero
rows, producing one 616.392-second segment.

The segment packet's 20/50/80% samples locally favor cardinal 0 but leave about
123 seconds unseen at both ends and 185 seconds between samples. They cannot
support one whole-segment primary or temporal-consistency claim. Relevance
therefore abstains. The global plan retains cardinal 0 at objective zero,
sets `production_eligible=false`, and emits no renderer command.

This is a useful negative result: motion difference detects movement and
capture discontinuity, not the known lift → own skiing → other-skiers story
structure. Do not lower thresholds to manufacture chapters.

## Repository state

- Expected branch: `main`; baseline/remote before checkpoint: `ad1508b`.
- New code should be the dedicated runner and its tests only.
- External full-source artifacts remain untracked.

## Verified

- Frame-difference samples SHA:
  `4b234059251cce8af1a0b55fff5a969f910c735d478f5230769be8d8d622565f`.
- Onset candidates SHA:
  `92ca4a507a09ace83c49aa64fcd7f4cc0aabea7bbdcb09dd6f208753b70f0a35`.
- Typed timeline SHA:
  `30f325d835154e6d837d7d9367823181b982af8a6fee23b3b9215657614d8398`.
- Fail-closed plan SHA:
  `b3f16984eee07d6ed0ba7cb50037d5434b859f0d521b946af61482ac9452a64f`.
- Dedicated runner focused suite: 27 tests pass before integration.
- Full suite: 508 tests pass; handoff and diff checks pass.
- Onset and full-segment temporary pixels were deleted and absence verified.

## Rejected

- Frame-difference onset as the sole story-boundary detector.
- Treating zero authorized motion onsets as proof of one coherent story state.
- Labeling a 616-second segment from three isolated stills.
- Concatenating independently classified windows and resetting hysteresis.
- The legacy hand-authored 390-second pilot split as source evidence.
- Redundant renders that are decision-identical to an existing baseline.

## Pending

- Inventory existing cheap scene/context signals before writing a new detector.
- Define a path-free chapter-proposal contract that schedules sparse semantic
  review but grants no boundary by itself.
- Test it against the known Skiing sequence and negative motion-onset result.
- Keep VLM use sparse; do not sample every second or make user review a runtime
  dependency.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After checkpointing, read ADR 0010 and the current event/story signal modules.
Prefer reusing low-cadence color/scene, audio, detector-presence or motion-state
summaries before adding a model. Record why each signal can detect gradual
chapter changes that raw frame difference missed.

## External artifacts

Set `AEGIS_DATA_DIR` locally. Full-source artifacts are under
`outputs/continuous-onset/skiing-full-v1/`; exact hashes and classifications
are in `docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`.
Never commit media, JSON evidence or review pixels from that directory.

## Active agents

No delegated work remains active. Implementation and both independent visual
reviews have returned completion packets.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis/rendering remain offline; downloads require explicit authority.
- Keep decode queues and memory bounded for 16 GB unified memory.
- Geometry, faces and mouth motion do not establish identity or speech.
- Git history is the archive; status and handoff contain current state only.
- Stop only for a real user decision, new authority or external dependency.
