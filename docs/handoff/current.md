# Current handoff

Updated: 2026-09-06T18:30:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 26e9870
Remote status: `origin/main` at `26e9870` before this checkpoint
Working tree at checkpoint: blind negative result and transient renderer

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The proposal policy has run exactly once;
the first blind review is complete and rejects that policy as a chapter detector.

## Last completed milestone

Commit `26e9870` records the frozen proposal result and exact private/public
schedule contract. The one permitted execution emits review-only proposals at
seconds 46 and 297; frozen hash-lattice controls are 200, 140 and 460. No rule
was retuned, and no proposal has semantic or boundary authority.

This checkpoint adds an exact private schedule/public neutral projection
contract. A 64-hex private salt is file-only; salted opaque IDs and order are
recomputed before atomic publication. The public projection contains ordinal,
qualitative row roles, neutral media references, four anonymous view slots and
questions only. It excludes absolute times, offsets, cardinal directions,
yaw/FOV, scores, hashes, candidate/control labels and source rationales.

## Repository state

- Expected branch/remote before checkpoint: `main` at `26e9870`.
- Expected dirty files are renderer module/CLI/test, the updated proposal-result
  experiment record, status and this handoff.
- External proxy, feature/proposal JSON, private key/salt and review pixels stay
  untracked.

## Verified

- Proposal artifact SHA:
  `eeddadd92e86478aea79d4659b0ed8edb0fbcc92e74ddc57b7f051a29fa146f3`.
- Policy/protocol hashes are recorded in the proposal experiment document.
- Renderer focused suite: 3 tests pass; full suite: 534 tests pass.
- Exact rebuild rejects private HMAC/ID/order and public bundle-ID mutations.
- Renderer separates lineage/source and proxy hashes, uses proxy time, strips
  PNG metadata, validates exact refs and publishes atomically.

## Rejected

- Frame-difference onset or active scene score as the sole chapter detector.
- Looking at Skiing feature values before freezing the proposal policy.
- Top-six selection, family quotas or threshold relaxation that backfill weak
  proposals.
- Treating proposal coverage as sufficient segment-evidence coverage.
- Requiring the owner to label proposal packets.
- The frozen persistent-state policy as a chapter detector: both proposals are
  observed negatives and one of three controls exposes a miss.

## Pending

- Commit and push the renderer and blind negative result.
- Audit descriptor values around 46/200/297 without retuning the frozen policy.
- Precommit a successor signal hypothesis and evaluate it on separate evidence.
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

After checkpointing, inspect why RGB/persistence descriptors favor the two
observed negatives over the second-200 transition. Do not retune the frozen
policy or infer boundaries from proposal times.

## External artifacts

Set `AEGIS_DATA_DIR` locally. The full proxy is under
`outputs/analysis-proxies/skiing-full-ffv1-v1/`; proposal material is under
`outputs/chapter-proposals/skiing-blind-v1/`. Never commit external artifacts.

## Active agents

None. The read-only numeric audit is complete. The main agent owns independent
evidence selection and the successor-hypothesis freeze. Proposal execution must
not be rerun or retuned.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- Frame memory is bounded; compact JSON rows grow at one row per second and do
  not establish arbitrary-duration constant memory.
- The 0.08 proposal floor is a pre-data hypothesis, not a probability.
- Proposals cannot create semantics, boundaries, camera paths or renders.
- Git history is the archive; status and handoff contain current state only.

## Frozen review schedules

- Private schedule SHA:
  `7f09f628c30575ddd9934816e2e2af32c219fb2b494ef91d14bccc8d81b81463`.
- Public reviewer-index SHA:
  `dd26f02b347467628aad92504070fd6399a1f00a8bc753ce3a49a239f7cad0b4`.
- The external salt is mode 0600 and its raw value is neither logged nor
  committed. Five packets were published atomically.
- Public transient bundle: five packets and 30 sanitized 960x540 RGB PNGs;
  path-independent tree SHA
  `7163a4f54c6daf919a40465dad785050ba0b12061da790b6a33096114c461159`.

## Blind result

- Both reviewers: packet 2 `story_change`; packets 1/3/4/5
  `no_semantic_change`.
- Post-review mapping: packet 2 is the second-200 control; packets 1 and 4 are
  proposals at seconds 297 and 46. Controls 140 and 460 are observed negatives.
- The policy therefore emits two observed negatives and misses one observed
  control transition. This rejects promotion but is not a calibrated rate.
- Next: read-only descriptor audit at 46/200/297, then precommit a successor
  signal hypothesis on separate evidence. No production video is authorized.

## Causal diagnosis

- RGB persistence scores are 0.3114 at 46, 0.0230 at 200 and 0.3044 at 297.
  The coarse representation favors palette/exposure/environment changes over
  the smaller station/person/infrastructure layout used by reviewers.
- The 297 and 337 reciprocal peaks share the [307,327) middle state and express
  one A→B→A excursion. Separation suppresses the exit but does not model it.
- Existing 15-second RGB change also favors appearance excursions and is not a
  justified fix. No threshold or policy was changed.
- Successor hypothesis: color-independent tilewise structural occupancy plus
  explicit episode/return reasoning, precommitted before separate evidence.
