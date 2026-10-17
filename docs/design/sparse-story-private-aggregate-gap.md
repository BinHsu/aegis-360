# Synthetic aggregate authority boundary

Status: local synthetic-gate pass authority verified; Stage A/B remain closed

The protocol's `synthetic_gate` aggregate is a runner-operational claim for one
scheduled packet. It needs a validated capability receipt, exact retained
schedule and manifests, one packet invocation with published receipt/evidence,
the complete synthetic case result, and owned cleanup before an aggregate can
be published. The 37 fixture cases, two fresh repeats, and the scheduled packet are now
bound by a private 40-claim proof. The completed local pass now derives a
public runner-operational aggregate after all 40 owners close; this grants no
semantic or production inference authority.

| Protocol prerequisite | Current evidence | Remaining boundary |
| --- | --- | --- |
| Exact case manifest and result | A 37-row frozen manifest runs in order with retained claims. Two additional native claims reproduce stdout. Public derivation, validation and serialization accept only the exact live 39-claim proof or its separate in-process sealed post-cleanup result/manifest snapshot. A shape-valid alternate result with a recomputed hash is rejected. | The finalized snapshot carries prior validation through cleanup and supplies the aggregate's exact case-result hash. It is no cryptographic signature. |
| Isolation capability | The 14 observed booleans rebuild from the exact native probe event, raw transcript and retained policy. Public derivation and validation accept only the live, uninvoked scheduled synthetic packet; copied capture, changed policy and shape-valid divergent receipt are rejected. | Validated bytes are captured before ordinary invocation, then sealed and hash-bound to the aggregate after cleanup. Do not claim universal confinement or kernel attestation. |
| Scheduled packet invocation | One separate normal-mode synthetic packet runs through the retained native launcher with the exact request bytes, a one-shot ordinary-mode ledger event and group-absence proof. The private schedule binds the live runtime manifest. | The fixture consumes bounded stdin through EOF but does not parse the request; this is transport evidence, not semantic request interpretation. Public invocation authority remains closed. |
| Receipt and evidence publication | The scheduled packet has its own private receipt and exclusive evidence/receipt peers. Public run-receipt derivation and validation require the exact live publication proof; a shape-valid divergent receipt or replaced peer is rejected. Before cleanup, the finalized snapshot captures its validated canonical receipt bytes and the previously validated capability bytes. | Public receipt authority expires with the live claim. The sealed snapshot carries the exact bytes and hashes through cleanup into the aggregate. |
| Aggregate inputs and publication | A private live proof joins the 37 cases, two repeats and distinct scheduled packet to the same packet ID, manifest, runtime, schedule, backend, runner policy, compiled policy, capability receipt, run receipt and evidence hashes. One 40-claim Seatbelt host test passes and finalizes all 40 owned sessions. A regression control found the old final snapshot accepted a changed case-result hash. The corrected snapshot seals retained hashes, checks scratch-root absence and exact published peers, and reports a missing publication root as a gate failure. An old-code host regression raised FileNotFoundError; the fixed test passes. A Grok Low Fast review found that the owner root could be substituted while the old peer paths remained live; a red host control proved this and both scheduled publication and final snapshot now bind the owner to exact peer paths. Its other two findings were excluded by schedule candidate identity and scratch cleanup checks. The close-time snapshot is a consistency proof over retained facts, not a defence against coordinated in-process mutation of its fields and seal. | Completed synthetic_gate pass derives only from the exact finalized proof. One exclusive result.json publication and byte-for-byte readback pass the native 40-owner host test; changed input hashes and a recreated scratch path invalidate authority. |

The aggregate retains exact private schedule bytes that were revalidated
before cleanup and sealed afterward; its `schedule_sha256` is private lineage,
not a new public schedule schema. The scheduled fixture
proves request transfer and EOF at the transport layer, not that the child
interpreted the canonical request. No model or real media acquisition follows.
The next acceptance gate is exact-commit CI after authorized push; Stage A/B
and semantic results stay closed.

## Capability authority review, 2026-10-17

A bounded Claude Opus 5.5 design review separated launcher handoff, observed
Seatbelt behavior and attribution. The local launcher verifies exact policy
bytes and passes them to `sandbox-exec -p`; the retained native event and 14
sentinel outcomes support this host-bound claim. They are not a kernel
attestation of installed bytes or a universal confinement proof. The reviewer
proposed an `allow default` differential run to expose denials caused by an
outer sandbox or ordinary filesystem permissions. We did not run or adopt that
proposal: the frozen renderer explicitly excludes `allow default`, and such a
run could permit real forbidden read, write, process or socket operations.
Any future attribution control needs separately bounded harmless sentinels and
the same ownership and cleanup guarantees. This is an unsettled design question,
not a requirement silently added to the accepted protocol.

The review also questioned binding a probe to a later adapter launch. Local
source review confirms that the backend manifest already binds the backend
executable hash, launcher runtime manifest and OS build, while the candidate
revalidates policy and retained roots. The private scheduled path already
revalidates its exact candidate binding, ordinary-mode native launch event,
request and policy before publication; its host test observes one such launch.
The remaining work is to derive a public claim from those retained live proofs
without silently widening their scope. The native runtime is verified by path before
`sandbox-exec` executes it; the accepted protocol already records this
pathname-exec gap. Keep the public API closed until the exact claim and its
limits are explicit and tested. The review's assertion about undocumented
`sandbox-exec` failure semantics was not independently verified and is not
used as authority. Apple's developer support describes custom Seatbelt profiles
as unsupported for third-party development and `sandbox-exec` as deprecated:
<https://developer.apple.com/forums/thread/661939>.

References: `docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md`
(Isolated adapter-runner synthetic gate; exact subordinate contracts),
`docs/design/sparse-story-private-invocation.md`, ADR 0010.
