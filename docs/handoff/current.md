# Current handoff

Updated: 2026-10-18T16:00:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: f01fb6a
Remote status: local `origin/main` is `621c195`; the prior exact-SHA green CI
claim applies to `4b78e1a`. CI for `621c195` was not rechecked in this turn.
Working tree at checkpoint: verify with `git status --short --branch`.

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The Skiing RGB proposal policy and the
color-independent structural successor are both rejected. The next bounded
direction is cheap-signal scheduling followed by sparse, closed semantic
observations without per-frame VLM inference.

## Last completed milestone

The Stage A real-media preflight exact-rebuilt and compared fourteen published
JSON files, then rendered six packets / 36 sanitized 960x540 PNGs from
manifest-hashed Old Ghost Road and Skiing sources. Two local runs and the
owner-authorized T7 publication have the same bundle-tree SHA-256
`fd65c7a5436829fadfd78a89b64d361f59a8934a98c8d3f3022dce3cebe6c5b1`
and result SHA-256
`c48862d316cbb5e3f05bc704d4eda5bcf7dd7d5269f0b9ca4db3be9962f6d80c`.
The external root was independently read back with exactly 37 files, expected
modes and hashes. Three representative 2x2 images were visually inspected.
See `docs/experiments/stage-a-media-preflight-2026-10-18.md`.

The owner clarified that the T7 `aegis-360-items` root is the project's
external asset space. Source media, models, proxies and pixel/audio-bearing
outputs belong there; checkout `outputs/` is for small plans/salts only. Two
mistaken 19 MiB local verification bundles were removed under owner code
`送 473` after dry-run per-leaf comparison with T7. Both roots are absent and
the external replacement remains intact; local `outputs/` measures 60 KiB.
The runner CLI now requires an explicit external data root and rejects durable
outputs outside it. The prior error was treating gitignore as a storage rule.

Full portable discovery on macOS 27.0.1 ran 946 tests with 97 skips and no
errors after the host test was corrected to expect fail-closed rejection of
`/usr/bin/sandbox-exec`'s extra ARM64 subtype. Native invocation proof is not
established on this OS. No model ran. Next review the changed OS backend and
pin/audit the native adapter.

## Prior Skiing rejection
- Proposals at 46/297 seconds are reviewed `no_semantic_change`; the 200-second
  control is `story_change`. RGB scores 0.3114/0.3044 versus 0.0230 at 200;
  the 297/337 pair is one A→B→A excursion. Reviewers agree on all five packets.
- Do not rerun, retune or lower the 0.08 floor. The external public review bundle
  tree SHA is
  `7163a4f54c6daf919a40465dad785050ba0b12061da790b6a33096114c461159`.

## Repository state

- Published `BinHsu/aegis-360@4478a4d` has green exact-SHA CI
  (`handoff-contract` run 39021685116).
- Aggregate gaps are recorded in `docs/design/sparse-story-private-aggregate-gap.md`.
  The local synthetic aggregate is complete; Stage A smoke is the next gate.

## Verified

- Published synthetic gate: 911 portable tests (814 passed, 97 skipped),
  native 40-owner host gate passed; exact-SHA remote CI green at `4b78e1a`.
- Stage A preflight: fourteen-file external bundle readback matched the
  authorized plan; source and weight hashes matched manifests.
- Current media acquisition: two local runs and one T7 publication produce
  the same closed hashes. Full discovery: 946 tests, 97 skipped, no failures.
  The host proof still rejects macOS 27.0.1.

## Rejected

- The Skiing RGB-persistence policy as a chapter detector.
- Treating the passing primary pair as accuracy or hiding the secondary reversal.
- Retuning either frozen experiment after seeing its result.

## Pending

- Local media duplicates are removed; T7 is the canonical media location.
  The current OS requires a new bounded backend review;
  native invocation authority is closed. A pinned/audited native adapter and
  full runtime asset proof remain missing. No model inference.
- No production render or retuning of rejected descriptors is authorized.

## Next commands

```sh
cd ~/Documents/aegis-360
git status --short --branch
python3 -m unittest tests.test_sparse_story_stage_a_render -v
python3 -m unittest tests.test_stage_a_media_preflight -v
python3 -m unittest tests.test_stage_a_preflight_bundle -v
python3 scripts/check_handoff.py
# Host test expects fail-closed proof on macOS 27.0.1.
python3 -m unittest tests.test_sparse_story_os_backend -v
git diff --check
git status --short
```

## External artifacts

Set `AEGIS_DATA_DIR` locally. Skiing material is under
`outputs/chapter-proposals/skiing-blind-v1/`. The new structural result is
`outputs/structural-chapter-contrast/old-ghost-road-labeled-v1.json`; selection
proof is `outputs/structural-blind-selection/old-ghost-road-v1.json` with SHA
`ad6f29b1…2a567`. Never commit external artifacts.

## Active agents
No delegated work is running. Independent read-only reviews of the scheduled
packet identified runtime-manifest binding and no-spawn cleanup gaps; both were
fixed and tested locally.

The owner requested a post-reboot Zellij resume command. The local session is
`vitreous-hill`; `scripts/resume_zellij_after_reboot.sh` checks the checkout,
Zellij installation and nesting, then attaches without creating a replacement
or force-running restored commands. Shell syntax and a stubbed safe path pass;
an actual reboot/reattach is unverified.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- This label-selected contrast is not source-level held-out evidence, accuracy
  or an effect-size claim.
- Git history is the archive; status and handoff contain current state only.
