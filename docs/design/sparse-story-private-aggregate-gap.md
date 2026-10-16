# Private synthetic aggregate gap

Status: design inventory, no aggregate authority

The protocol's `synthetic_gate` aggregate is a runner-operational claim for one
scheduled packet. It needs a validated capability receipt, exact retained
schedule and manifests, one packet invocation with published receipt/evidence,
the complete synthetic case result, and owned cleanup before an aggregate can
be published. The 37 fixture cases and two fresh repeats are separate private
evidence; they do not themselves constitute the scheduled packet row.

| Protocol prerequisite | Current evidence | Remaining boundary |
| --- | --- | --- |
| Exact case manifest and result | A 37-row frozen manifest runs in order with retained claims. Two additional native claims reproduce stdout. Private result bytes and SHA revalidate from live proofs. | Public case-result derivation/validation remains closed. Its independent authority review has not run. |
| Isolation capability | One retained native probe has 14 observed boolean outcomes and private receipt bytes. | Public capability derivation/validation remains closed. Bind the actual installed-policy evidence to the scheduled packet before an authority claim. |
| Scheduled packet invocation | Individual fixture cases use exact retained native launcher, policy, environment and one-shot ledgers. | Bind one scheduled packet's normal invocation, stdout and group/cleanup proof. The 37 fixture calls cannot be counted as its single packet invocation. |
| Receipt and evidence publication | Private receipt bytes rebuild for native fixture cases. Exclusive two-peer publication and replacement refusal have separate tests. | Publish and revalidate the scheduled packet's own two peers without replacement, then verify identity-owned cleanup on failure. |
| Aggregate inputs and publication | Shape validator fixes the hashes, one ordered packet row, lifecycle stage and pass/reject/invalid precedence. | Derive hashes from retained schedule/backend/policy/capability/case/publication proofs, publish the final aggregate exclusively and read it back. Public aggregate APIs remain closed. |

Next bounded implementation: retain a schedule-bound, single-packet synthetic
invocation proof through exact receipt/evidence publication. Require the same
candidate, launcher, installed policy, group absence, one-shot ledger and
post-exit root checks already used by the fixture cases. A fabricated receipt,
changed evidence peer, missing group-absence proof or second invocation must
prevent aggregate construction. This work uses only synthetic fixture assets;
no model or real media acquisition follows from it.

References: `docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md`
(Isolated adapter-runner synthetic gate; exact subordinate contracts),
`docs/design/sparse-story-private-invocation.md`, ADR 0010.
