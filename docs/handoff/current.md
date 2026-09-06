# Current handoff

Updated: 2026-09-06T21:10:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 011d8b8
Remote status: `origin/main` at `011d8b8`
Working tree at checkpoint: blind selection-policy freeze

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The first Skiing chapter-proposal policy
is rejected; a color-independent structural successor now requires blind
replication after one bounded labeled contrast.

## Last completed milestone

The frozen Old Ghost Road contrast config SHA is
`8baf66a00a008625cd91292aaa8ac0a8794d9fb20338e0acfab054b3a2f7f7a2`.
It ran once using direct-source 2-fps 160x80 gray frames, exact rational sample
mapping, closed label/packet/evidence hashes and source hashes before/after.

- Result artifact SHA:
  `83ba3f456f1d56b9bc40fef413cbc93009c0fd4c4813c85f9004614fc8843346`.
- Primary passes: chapter/activity event 0008 scores 0.15776835; within-chapter
  action event 0005 scores 0.08512510.
- Correlated secondary reverses: chapter event 0019 scores 0.02279322; within-
  chapter event 0018 scores 0.03082203. This contrary evidence is report-only
  by precommit but prevents any general detector claim.
- All eight exact A→B→A fixtures pass. Source hashes before/after match.
- Authority is blind-replication design only: no story boundary, camera choice
  or render.

## Prior Skiing rejection

- Frozen visual-state proposals at 46 and 297 seconds are independently
  reviewed `no_semantic_change`; the unlabeled 200-second control alone is
  `story_change`. Two reviewers agree on all five packets.
- Numeric audit shows palette-dominated RGB scores 0.3114/0.3044 at 46/297 and
  only 0.0230 at 200. The 297/337 pair is one A→B→A appearance excursion.
- Do not rerun, retune or lower the 0.08 floor. The external public review bundle
  tree SHA is
  `7163a4f54c6daf919a40465dad785050ba0b12061da790b6a33096114c461159`.

## Repository state

- Expected branch/remote before checkpoint: `main` at `011d8b8`.
- Expected dirty files: selection config, replication doc/index and handoff.
- External source, numeric artifacts, private key/salt and review pixels stay
  untracked.
- Full suite: 538 tests pass before result-document integration.

## Verified

- Frozen source/config/fixture and four evidence lineages exact-validate.
- Primary structural ordinal gate and all eight synthetic episode gates pass.
- Result artifact is path-free and grants no production authority.

## Rejected

- The Skiing RGB-persistence policy as a chapter detector.
- Treating the passing primary pair as accuracy or hiding the secondary reversal.
- Retuning either frozen experiment after seeing its result.

## Pending

- Commit and push selection policy SHA `c4a1f411…f2e6cb`.
- Implement its exact 26-entry self-proving selection artifact.
- Replication must use neutral packets and fresh independent reviewers before
  opening event identities/positions. Do not render production video.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

## External artifacts

Set `AEGIS_DATA_DIR` locally. Skiing material is under
`outputs/chapter-proposals/skiing-blind-v1/`. The new structural result is
`outputs/structural-chapter-contrast/old-ghost-road-labeled-v1.json`. Never
commit external artifacts.

## Active agents

None. Independent pre-score audit passes the selection policy. The main agent
owns its freeze checkpoint and self-proving builder delegation.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- This label-selected contrast is not source-level held-out evidence, accuracy
  or an effect-size claim.
- Git history is the archive; status and handoff contain current state only.
