# Private synthetic aggregate gap

Status: design inventory, no aggregate authority

The protocol's `synthetic_gate` aggregate is a runner-operational claim for one
scheduled packet. It needs a validated capability receipt, exact retained
schedule and manifests, one packet invocation with published receipt/evidence,
the complete synthetic case result, and owned cleanup before an aggregate can
be published. The 37 fixture cases, two fresh repeats, and the scheduled packet are now
bound by a private 40-claim proof. That proof is not a public aggregate.

| Protocol prerequisite | Current evidence | Remaining boundary |
| --- | --- | --- |
| Exact case manifest and result | A 37-row frozen manifest runs in order with retained claims. Two additional native claims reproduce stdout. Private result bytes and SHA revalidate from live proofs. | Public case-result derivation/validation remains closed. Its independent authority review has not run. |
| Isolation capability | One retained native probe has 14 observed boolean outcomes and private receipt bytes. | Public capability derivation/validation remains closed. Bind the actual installed-policy evidence to the scheduled packet before an authority claim. |
| Scheduled packet invocation | One separate normal-mode synthetic packet runs through the retained native launcher with the exact request bytes, a one-shot ordinary-mode ledger event and group-absence proof. The private schedule binds the live runtime manifest. | The fixture consumes bounded stdin through EOF but does not parse the request; this is transport evidence, not semantic request interpretation. Public invocation authority remains closed. |
| Receipt and evidence publication | The scheduled packet has its own private receipt and exclusive evidence/receipt peers. Exact bytes revalidate; replacement refuses cleanup and preserves the replacement. | Public receipt/publication authority remains closed. |
| Aggregate inputs and publication | A private live proof joins the 37 cases, two repeats and distinct scheduled packet to the same packet ID, manifest, runtime, schedule, backend, runner policy, compiled policy, capability receipt, run receipt and evidence hashes. One 40-claim Seatbelt host test passes and finalizes all 40 owned sessions. A regression control found the old final snapshot accepted a changed case-result hash. The corrected snapshot seals retained hashes, checks scratch-root absence and exact published peers, and reports a missing publication root as a gate failure. An old-code host regression raised FileNotFoundError; the fixed test passes. The close-time snapshot is a consistency proof over retained facts, not a defence against coordinated in-process mutation of its fields and seal. | Review the close-time snapshot as an authority boundary, then derive and validate public capability, case-result and aggregate authority, publish the aggregate exclusively and read it back. Public aggregate APIs remain closed. |

Next bounded implementation: independently review the remaining public case-result,
capability and aggregate authority boundaries. The private schedule shape has no
protocol-defined public schema. Do not derive a public aggregate hash from its
private bytes without a separately validated authority. The scheduled fixture
proves request transfer and EOF at the transport layer, not that the child
interpreted the canonical request. No model or real media acquisition follows.

References: `docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md`
(Isolated adapter-runner synthetic gate; exact subordinate contracts),
`docs/design/sparse-story-private-invocation.md`, ADR 0010.
