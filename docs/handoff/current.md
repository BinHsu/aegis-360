# Current handoff

Updated: 2026-09-06T16:20:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 26ee87f
Remote status: `origin/main` at `26ee87f` before this checkpoint
Working tree at checkpoint: frozen visual-state, proposal and blind protocol

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. Visual-state acquisition is accepted and
the proposal policy is frozen; the next gate is its one blind Skiing execution.

## Last completed milestone

Commit `26ee87f` provides the canonical lossless 960x480/10-fps FFV1 proxy. The
full Skiing proxy has 6,164 frames over 616.400 seconds, exact source/config/
proxy lineage, deterministic decoded pixels and no semantic authority.

This checkpoint adds `visual-state-features.v1`: 1-fps 96x48 RGB sampling with
luma, 4x2 spatial luma, RGB histogram, edge and five/15-second descriptors.
Decoded-frame memory is bounded to the current frame plus 16 history frames.
The full Skiing acquisition emits 616 rows in 859,874 bytes. A repeat takes
22.93 seconds and is byte-identical. The initial real run safely exposed and
fixed the FFmpeg near-rounded sample-count rule. No feature value, peak or
timestamp was inspected while the proposal policy was designed.

The separate `chapter-proposal-candidates.v1` policy compares complete
half-open 20-sample before/after states around a 20-second guard, subtracts
both within-state dispersions, and requires `max(0.08, median + 3*MAD)`. It
uses a 10-second local radius, earliest plateaus and 45-second separation,
never backfills, caps at six, audits every local maximum and grants review
authority only. The blind protocol fixes fresh-context two-reviewer packets
and a deterministic hash-ordered control procedure.

## Repository state

- Expected branch/remote before checkpoint: `main` at `26ee87f`.
- Expected dirty files are two configs, four modules/CLIs, two test files, two
  experiment records, documentation indexes, status and this handoff.
- External proxy, feature JSON and future review pixels remain untracked.

## Verified

- Visual-state artifact SHA:
  `81c92d89cc51190145e89fd5d02a95c5e480794fa22e0127dafd84b9391b2c91`.
- Visual-state repeat: byte-identical; 22.93 seconds wall time.
- Visual-state focused suite: 6 tests pass after the real count fix.
- Proposal focused suite: 8 tests pass.
- Full suite before documentation integration: 526 tests pass.
- Proposal synthetic gates: constant and transient emit zero; persistent and
  separated family changes emit bounded ordered proposals.
- Proposal config and protocol were completed without external artifact access.
- RSS, swap and thermals were not measured and are not claimed.

## Rejected

- Frame-difference onset or active scene score as the sole chapter detector.
- Looking at Skiing feature values before freezing the proposal policy.
- Top-six selection, family quotas or threshold relaxation that backfill weak
  proposals.
- Treating proposal coverage as sufficient segment-evidence coverage.
- Requiring the owner to label proposal packets.

## Pending

- Commit and push this pre-proposal freeze point.
- Create a separate external hidden coarse key and record its checksum.
- Record committed proposal-policy and protocol hashes.
- Execute the frozen proposal CLI once; never retune it on this result.
- Resolve three controls using the frozen 10-second hash-ordered lattice.
- Run two independent fresh-context reviews before any typed boundary.
- Chapters longer than about 90 seconds or evidence gaps over 30 seconds must
  receive denser segment review or abstain. No video awaits owner review.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After checkpointing, hash the committed protocol/policy/key, run the proposal
CLI once against the existing visual-state artifact, then resolve controls.
Do not modify old scene/onset schemas and do not render.

## External artifacts

Set `AEGIS_DATA_DIR` locally. The full proxy is under
`outputs/analysis-proxies/skiing-full-ffv1-v1/`; the feature artifact is
`outputs/visual-state/skiing-full-1fps-v1.json`. Exact acquisition evidence is
in `docs/experiments/analysis-proxy-60s-protocol.md` and
`docs/experiments/skiing-visual-state-features-v1-2026-09-06.md`. Never commit
the external artifacts.

## Active agents

No delegated work remains active. Three agents completed feature acquisition,
proposal implementation and independent blind-protocol audit without inspecting
external feature values. The main agent owns the freeze commit and execution.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- Frame memory is bounded; compact JSON rows grow at one row per second and do
  not establish arbitrary-duration constant memory.
- The 0.08 proposal floor is a pre-data hypothesis, not a probability.
- Proposals cannot create semantics, boundaries, camera paths or renders.
- Git history is the archive; status and handoff contain current state only.
