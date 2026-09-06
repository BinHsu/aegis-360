# Current handoff

Updated: 2026-09-06T17:10:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 00f9c76
Remote status: `origin/main` at `00f9c76` before this checkpoint
Working tree at checkpoint: proposal result and blind review schedule contract

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The proposal policy has run exactly once;
the next gate is a neutral private/public review schedule and transient packets.

## Last completed milestone

Commit `00f9c76` freezes the visual-state feature stream, proposal policy and
blind protocol before real feature inspection. The one permitted execution
emits review-only proposals at seconds 46 and 297; a qualified second-337 peak
is separation-suppressed. Frozen hash-lattice controls are 200, 140 and 460.
No rule was retuned, and no proposal has semantic or boundary authority.

This checkpoint adds an exact private schedule/public neutral projection
contract. A 64-hex private salt is file-only; salted opaque IDs and order are
recomputed before atomic publication. The public projection contains ordinal,
qualitative row roles, neutral media references, four anonymous view slots and
questions only. It excludes absolute times, offsets, cardinal directions,
yaw/FOV, scores, hashes, candidate/control labels and source rationales.

## Repository state

- Expected branch/remote before checkpoint: `main` at `00f9c76`.
- Expected dirty files are the schedule config/module/CLI/test, proposal-result
  experiment record, documentation index, status and this handoff.
- External proxy, feature/proposal JSON, private key/salt and review pixels stay
  untracked.

## Verified

- Proposal artifact SHA:
  `eeddadd92e86478aea79d4659b0ed8edb0fbcc92e74ddc57b7f051a29fa146f3`.
- Policy/protocol hashes are recorded in the proposal experiment document.
- Schedule focused suite: 5 tests pass; full suite: 531 tests pass.
- Exact rebuild rejects private HMAC/ID/order and public bundle-ID mutations.
- Schedule implementation and audits did not inspect external artifacts.

## Rejected

- Frame-difference onset or active scene score as the sole chapter detector.
- Looking at Skiing feature values before freezing the proposal policy.
- Top-six selection, family quotas or threshold relaxation that backfill weak
  proposals.
- Treating proposal coverage as sufficient segment-evidence coverage.
- Requiring the owner to label proposal packets.

## Pending

- Commit and push the proposal result and review-schedule contract.
- Create a separate external salt, then generate and hash both schedules.
- Implement an exact-validated transient four-cardinal packet renderer.
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

After checkpointing, create the private salt and exact schedules. Freeze their
hashes before implementing/rendering the neutral packets. Do not modify old
scene/onset schemas and do not infer boundaries from proposal times.

## External artifacts

Set `AEGIS_DATA_DIR` locally. The full proxy is under
`outputs/analysis-proxies/skiing-full-ffv1-v1/`; proposal material is under
`outputs/chapter-proposals/skiing-blind-v1/`. Never commit external artifacts.

## Active agents

None. Schedule implementation and independent leakage audit are complete. The
main agent owns external schedule generation, packet rendering and review
dispatch. Proposal execution must not be rerun or retuned.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- Frame memory is bounded; compact JSON rows grow at one row per second and do
  not establish arbitrary-duration constant memory.
- The 0.08 proposal floor is a pre-data hypothesis, not a probability.
- Proposals cannot create semantics, boundaries, camera paths or renders.
- Git history is the archive; status and handoff contain current state only.
