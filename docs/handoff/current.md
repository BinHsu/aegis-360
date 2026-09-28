# Current handoff

Updated: 2026-09-29T05:01:35+08:00
Repository: aegis-360
Branch: main
Baseline commit: 70e6a41
Remote status: `main` and fetched `origin/main` match at
`70e6a41848d39e1136877cde705f748e1345f776`.
GitHub Actions `handoff-contract` run 36487076999 succeeded for that exact SHA.
Working tree at checkpoint: clean after local commit; verify with
`git status --short` before resuming.

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The Skiing RGB proposal policy and the
color-independent structural successor are both rejected. The next bounded
direction is cheap-signal scheduling followed by sparse, closed semantic
observations without per-frame VLM inference.

## Last completed milestone

The published implementation `edcbe3a` freezes the
canonical adapter request and runner-policy bytes, real/effective uid/gid and
retained private HOME/TMPDIR identities. HOME and TMPDIR must be distinct,
nonoverlapping empty directories beneath scratch, so their writes remain inside
the sole policy write allowance. It derives exact media leaves from the existing
sanitizer/lineage gate, retains them with asset-tree named-path and child-map
checks, and rebuilds canonical policy bytes only after revalidating all roots.
Multi-packet execution roots, aliases, overlapping roots, changed content,
replaced names and extra leaves fail closed. Close releases owned input proofs
and never closes the borrowed facade or deletes caller assets.

Only path-free policy and invocation-binding digests are exposed. The candidate
grants no spawn, installed-policy, receipt or capability authority.
Its internal synthetic-support manifest is solely a retention representation;
the original media result remains the source of input-derived authority.
Full-set-to-one-packet candidate retention now has synthetic integration evidence.
Validated 6/24-packet projection sets now select a stable one-packet projection
and copied private packet. A verified full media result and tree yield exactly
the selected six original payloads; tests publish and validate first/last
derived bundles. This input selector grants no execution-bundle authority.
The selected inputs now feed the existing atomic media publisher, producing
the one-packet bundle and result without replacement. Focused tests validate
both first and last selected bundles; a repeated publication at the same
destinations is refused and preserves the first result.
An integration test publishes packet six from a validated six-packet set,
opens the resulting one-packet batch candidate and checks its policy includes
only the selected bundle root. Mutating a selected media leaf invalidates the
candidate binding. This is synthetic local proof, not an invocation or
capability result.

The synthetic native fixture compiles as a thin signed arm64 Mach-O outside Git.
One retained entrypoint accepts the closed 21-row probe mode and 33 adapter-owned
case IDs: literal argv, seven stdout failure forms, exact environment, descriptor
hygiene, cwd identity, three stdout ceilings, stderr, nonzero exit, signal exit
and wall timeout, concurrent stdin/stdout pressure, TERM-ignore/KILL, known-file
read/write attempts, live loopback/AF_UNIX connect attempts and child fork.
The other four frozen cases require coordinator verification. Positive
cases emit a schema-valid abstention. Host
tests verify the manifest before and after both modes and reject malformed
mode/argv. Negative tests detect extra/missing/wrong environment entries,
inherited descriptors and incorrect cwd. This is unsandboxed fixture evidence only;
the remaining case matrix, capability probe, policy installation and coordinator
are pending.

The new private allowed-probe selector reads the first request-bound media leaf,
one model leaf and `prompt.txt` through their retained file descriptors. It
returns only transient paths and at most 128-byte prefixes after pre/post root
revalidation. A changed model leaf fails.

The new private raw-row evaluator checks 21 operation values, errno and data
against the three allowed prefixes, yielding 14 provisional booleans. It cannot
prove the process/policy source or absence of side effects. One retained outside
sentinel tree now checks the existing file and absent create/rename names before
and after. The unconfined native probe changes that tree and fails revalidation.
An existing forbidden-read leaf can now be retained with no-follow descriptors,
bounded full-content digest and pre/post identity checks. Synthetic mutation,
replacement, unlink and unsafe-mode tests fail; actual repo/protocol files pass
the non-mutating check. Neighbor/result ownership and integration remain open.
The scratch snapshot now retains its rename source, requires exactly one allowed
scratch-write marker after probe and rejects fork/exec markers or private-directory
replacement. Live IPv4, IPv6 and AF_UNIX listeners check bound addresses, socket
path identity and zero accepted connections.
The private probe context now assembles exact 19-argument probe mode from the
batch candidate, four retained denied-read leaves, outside/scratch snapshots
and live listeners. It checks denial-path disjointness against retained policy
roots, then revalidates all inputs before and after. A changed neighbor leaf
fails postvalidation. The new private transport runs one bounded host raw probe
through the retained launcher, same retained runtime and exact policy. Its 21
rows and 14 provisional primitive values pass with postvalidation. A forced
pre-policy timeout emits no adapter output. These observations do not grant
capability authority.
The context fixes repository/protocol probes to actual source leaves. A new
private helper retains full-set neighbor/result leaves after validating the
full media result/tree and selected packet ID; it rechecks the full tree,
result file and candidate binding at exit. One-packet smoke still lacks a
distinct neighbor, and coordinator ownership of side-effect sentinels remains
open. No capability is issued.
The host fixture now selects packet six from a validated six-packet media set.
The forbidden neighbor is a real PNG leaf belonging to another packet in the
full bundle; the forbidden result is the full-set media gate result file.
Ten host transport tests pass through this setup, including a test that
changes the neighbor leaf after process exit and rejects the capture. This
does not yet make production neighbor/result selection coordinator-owned.
An attempted unconditional pre-reap `killpg` returned macOS `EPERM` for an
already-exited leader and was reverted before publication. A revised local
change keeps the leader unreaped with `waitid(WNOWAIT)`, signals its group,
tolerates `EPERM` only in that final exited-leader case, and still requires
post-reap group absence. A controlled host test now
leaves a child sleeping after the leader exits, verifies teardown, and fails
when group `SIGKILL` is suppressed. This closes that specific lifecycle defect;
other abnormal exit paths still require review.
The transport now marks completion only after its own closed parser accepts
all 21 rows and all 14 primitive value checks pass. Host tests force malformed
rows and a false primitive result after an otherwise clean run; both remain
invalid with return code zero and passing postvalidation. This closes the
previous gap where tests checked rows separately but the transport did not.
An owned TERM-ignoring process is now tested under a short timeout and grace:
the transport returns SIGKILL and confirms group absence. Suppressing group
SIGKILL makes the test fail; its fixture cleans up the exact process it spawned.
The raw transport now has a host test for stdout capture at the frozen
65,536-byte limit plus one proof byte. A process writes 131,072 bytes; the
capture retains exactly 65,537 and remains invalid. Raising the limit to
131,072 makes the regression fail.
The transport now compares the complete invocation-binding bytes before and
after execution. A host test appends JSON whitespace to the retained request
after process exit: all rows remain valid, but the binding changes and the
capture is invalid. The public capability and receipt APIs remain closed.
No capability token, receipt or spawn authority is created.

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

- Published checkpoint: `BinHsu/aegis-360@70e6a41`; GitHub Actions
  `handoff-contract` run 36487076999 succeeded for exact SHA
  `70e6a41848d39e1136877cde705f748e1345f776`.

## Verified

- Restricted full discovery: 761 tests run, 734 passed, 27 skips. Six listener
  subcases skipped because the shell sandbox denies local listener binds.
- Escalated host fixture: eight tests pass, including the three live-listener
  network cases and owned-child fork marker. No sandbox-confinement authority.
- A controlled probe-mode name mutation makes the original mode fail with exit 64.
- The allowed-leaf selector returns request-bound paths/byte prefixes; changing
  a retained model leaf makes its call fail.
- Closed raw-transcript parser and provisional row checks: five focused tests
  pass; malformed order and altered values are detected.
- Outside sentinel snapshot: three focused tests detect create, overwrite,
  truncate, rename, unlink, name replacement and mode change.
- Forbidden-read snapshot: four focused tests cover identity/content mutation,
  symlink/mode rejection and real repo/protocol file retention.
- Scratch snapshot: three focused tests cover expected write and rejected source,
  marker and private-directory changes. Escalated listener host gate: three tests
  pass, including successful connections to all three listener families.
- Escalated batch-policy host gate: 16 tests pass, including exact probe argv,
  disjointness, fixed source leaves and post-execution neighbor mutation rejection.
- Escalated raw transport host gate: ten tests pass, including 21-row
  evaluation, malformed/false-row rejection, timeout, post-exit mutation,
  owned-descendant teardown, TERM-ignore/KILL, stdout ceiling, changed binding
  and mutation of a real other-packet leaf.
  Suppressing group KILL fails both relevant lifecycle regressions.
- Full-set selection: two focused tests pass. Selected first/last packet
  bundles publish and validate; changed full result and replacement are rejected.
- Batch candidate integration: packet six selected from a six-packet set is
  retained; policy excludes the full-set root and a changed selected leaf fails.
- Retained full-set denials: two focused tests pass; changed result bytes/file
  and a selected packet absent from the full set fail before probe context use.
- Focused candidate/facade real-host integration: 34 tests run, all passed.
- Controlled mutation returning cached policy without revalidation causes the
  extra-neighbor-leaf regression to fail with `ValueError not raised`.
- Controlled mutation removing private-directory emptiness validation causes the
  nonempty-HOME regression to fail with `ValueError not raised`.
- Independent audit found no blocker within this non-authoritative boundary.
- `python3 scripts/check_handoff.py` and `git diff --check` passed.

## Rejected

- The Skiing RGB-persistence policy as a chapter detector.
- Treating the passing primary pair as accuracy or hiding the secondary reversal.
- Retuning either frozen experiment after seeing its result.

## Pending

- Provide a one-packet neighbor sentinel and coordinator-owned side-effect
  cleanup, then compose retained full-set proofs and validated raw rows into a
  private single-use capability.
  boundary; audit remaining abnormal process lifecycle cases. Passing
  provisional booleans cannot attest denial alone.
- The rejected transport defects and their disposition are recorded above; do
  not restore its source unchanged or treat its 21 passing tests as authority.
- Implement the same-entrypoint raw capability-probe transcript and private
  single-use composition boundary before restoring launcher transport. The next
  transport must use strong child ownership, bounded nonblocking policy delivery,
  exact stdio cleanup, lifecycle-based signal revocation and post-exit checks.
- Capability probing must use the same entrypoint/policy/roots as inference and
  known existing leaves; never add sentinel files to closed input bundles.
- Keep proof-accepting authority APIs closed. Do not acquire models or real-media
  packets until the implementation gate is reviewed and frozen.
- No production render or retuning of rejected descriptors is authorized.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 -m unittest tests.test_sparse_story_projection tests.test_sparse_story_media_tree -q
AEGIS_RUN_HOST_SEATBELT_TESTS=1 python3 -m unittest tests.test_sparse_story_raw_probe_transport -v
python3 scripts/check_handoff.py
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

None. The bounded protocol-boundary review and implementation audit completed.
The reviewer changed no files and independently ran the eight initial candidate
checks. Main agent integrated host evidence and added two more checks.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- This label-selected contrast is not source-level held-out evidence, accuracy
  or an effect-size claim.
- Git history is the archive; status and handoff contain current state only.
