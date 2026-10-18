# Current handoff

Updated: 2026-10-19T05:05:31+08:00
Repository: aegis-360
Branch: main
Baseline commit: 2819a76
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

The macOS 27.0.1 OS-backend parser now recognizes the SDK-documented
ARM64E/ARM64E_X1 pair and validates both slices. Old code rejects this host;
the updated retained host proof passes. Full discovery ran 947 tests with 97
skips and no failures. See
`docs/experiments/sparse-story-os-backend-arm64e-x1-2026-10-18.md`. This is a
backend proof only; native adapter and model invocation remain closed.

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
  the same closed hashes. Full discovery: 947 tests, 97 skipped, no failures.
  The macOS 27.0.1 retained OS-backend host proof passes.

## Rejected

- The Skiing RGB-persistence policy as a chapter detector.
- Treating the passing primary pair as accuracy or hiding the secondary reversal.
- Retuning either frozen experiment after seeing its result.

## Pending

- Local media duplicates are removed; T7 is the canonical media location.
  Native invocation authority is closed. A pinned/audited native adapter and
  full runtime asset proof remain missing. No model inference.
The owner approved the source-only official `mlx-swift-lm` `3.32.3` fetch. It
resolved to commit `3b339ad6e3b3f44c8121ecff5131c7fd55e075e6`, tree
`bbba5542694fbf2eaa3e8cfd053aa0e7edb8f79b`; the isolated checkout is
clean. The declared Swift dependencies have ranges and no resolution lock.
Syft did not inventory them, Trivy recognized zero language files, and Semgrep
failed before scanning. See
`docs/experiments/mlx-swift-lm-source-audit-2026-10-18.md`. No build,
dependency acquisition or model invocation occurred.
The owner clarified that third-party source intended for compilation and the
entire package cache/build scratch/products belong under the T7 project root,
without recurring location approval. The verified canonical source copy is
under the T7 project root's `sources/mlx-swift-lm-3.32.3`; its commit/tree
match the audited checkout. `AGENTS.md` now distinguishes the repository's
tracked source in Documents from acquired build inputs on T7. SwiftPM 6.4 has
package/scratch/cache path flags, but no build was run to verify placement.
SwiftPM `--help` unexpectedly created a two-file `.build` marker under the
Documents checkout; it was moved intact to the T7 build area and the checkout
is clean of that cache. Future SwiftPM probes need T7 paths from the outset.
The official `mlx-swift` `0.32.3` and `swift-syntax` `602.0.0` tag refs resolved
read-only to the commits in `docs/design/sparse-story-stage-a-readiness.md`.
Automatic approval review rejected both source-only clone attempts: a general
"continue" was not explicit authorization for this new network acquisition.
Neither dependency was downloaded. Obtain approval for the exact two-target
batch before retrying; no indirect workaround.
The agent-neutral global engineering contract already defines the send-code
gate for external changes. The earlier repo-local restatement was removed as
redundant; the repo policy retains only the T7 domain boundary. The exact two-source
plan remains unchanged. Its first code was revoked because the accompanying
message did not present the full material change; a fresh code is pending.
Neither dependency has been downloaded.
- No production render or retuning of rejected descriptors is authorized.

## Next commands

```sh
cd ~/Documents/aegis-360
git status --short --branch
python3 -m unittest tests.test_sparse_story_stage_a_render -v
python3 -m unittest tests.test_stage_a_media_preflight -v
python3 -m unittest tests.test_stage_a_preflight_bundle -v
python3 scripts/check_handoff.py
# The macOS 27.0.1 retained backend proof passes; invocation remains closed.
python3 -m unittest tests.test_sparse_story_os_backend -v
git diff --check
git status --short
```

Next owner decision: explicit authorization for the exact two-tag Swift
dependency source-only acquisition recorded in the readiness design. Do not
build, resolve transitives or execute under that approval.

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
