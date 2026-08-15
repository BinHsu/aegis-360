# Event semantic evidence

Status: Implemented contract; no model selected

## Boundary

`aegis360.event-semantic-evidence.v1` is the only durable output expected from
a sparse local semantic adapter. It binds one exact Event Review Packet and an
exact adapter config. It records observations, not an edit decision.

An observed result must cover every candidate that appears in the packet,
once and in first-appearance order. For each it may classify only visibility
(`clear`, `partial`, `obstructed`, `unknown`), event relevance (`primary`,
`supporting`, `unrelated`, `unknown`) and temporal consistency (`stable`,
`changing`, `unknown`). Event class and current/proposed relationship also use
closed enums. The schema contains no confidence number because model outputs
are not assumed calibrated.

`abstain` is a first-class result and must carry unknown event/relationship
values with an empty observation list. This prevents an adapter from hiding
claims behind an uncertainty flag.

## Ownership

- The packet owns event scope, timestamps and eligible candidate IDs.
- The checksummed context grid owns camera geometry.
- The semantic adapter owns only closed observations and abstention.
- A future evidence-to-utility adapter owns deterministic score conversion.
- The global planner owns all cut/view decisions and transition costs.

Model ID and exact model-asset SHA-256 are mandatory. Free text, paths, media,
names, identity, geometry, new candidates and renderer commands are forbidden.
The constrained raw-output JSON schema narrows decoding; the binder remains
the authority and rejects missing, invented or reordered candidates.

## Next gate

Do not acquire or tune a model yet. First define deterministic evidence-to-
utility behavior, especially the abstention fallback, and test it against the
existing owner-positive Gaudeamus and owner-negative Hundra labels without
feeding those labels into product input.
