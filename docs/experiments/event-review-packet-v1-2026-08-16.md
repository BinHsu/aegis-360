# Event review packet v1

Status: Executed on 2026-08-16

## Question and decision unlocked

Can each sparse timeline event become a bounded semantic-review request that
preserves temporal context and candidate availability without persisting
frames or importing the owner's answer? A pass unlocks a temporary media
renderer and replaceable local semantic adapter. It does not select a model or
authorize a camera cut.

## Contract and policy

`aegis360.event-review-packet.v1` binds the exact event-timeline and
context-view-grid SHA-256 values. One packet names one declared event and five
temporal roles:

1. up to two seconds before;
2. event 25 percent;
3. event midpoint;
4. event 75 percent;
5. up to two seconds after.

Context outside the declared analysis window is represented by a null
timestamp and no candidate IDs. The current candidate is scheduled at every
available timestamp. The proposed candidate is scheduled only when the
timestamp belongs to an availability interval recorded by the timeline.

The packet repeats machine evidence but no geometry. The checksummed grid owns
geometry; a later renderer resolves IDs against it. Durable pixels are
forbidden, rendering is restricted to declared candidates, and temporary media
must be deleted after adapter completion. Exact rebuilding rejects added
decisions or invented candidates.

## Execution and results

Environment: fanless M4 MacBook Air with 16 GB unified memory, macOS 26.5.2
(25F84). No model, source decode, FFmpeg run or network access was needed.

Three real packets were generated from Event Timeline v1:

- Gaudeamus opening: 7.0, 10.5, 12.0, 13.5 and 17.0 seconds. The audience
  candidate is eligible only at 12.0 and 13.5.
- Gaudeamus ending: 107.5, 113.25, 117.0, 120.75 and 126.5 seconds. The
  audience candidate is eligible only at 113.25 and 117.0.
- Hundra ending: 215.5, 219.75, 222.0 and 224.25 seconds; after-context is
  null because the analysis window ends at 226.5. The audience candidate is
  eligible at all three during-event anchors.

External artifacts, never committed:

- `outputs/event-review-packets/gaudeamus-reaction-v1/event-reaction-0000.json`,
  SHA-256 `5034e77b458d63dea9e51f0ee51a253eb5cd0d0fc6fef6bda5c8c40baf3df7ff`.
- `outputs/event-review-packets/gaudeamus-reaction-v1/event-reaction-0001.json`,
  SHA-256 `73f36e308ee9f7cacc681f1c517373855a3fab32f48448e00ae23b346738d9f2`.
- `outputs/event-review-packets/hundra-reaction-v1/event-reaction-0000.json`,
  SHA-256 `54a05dc6b3603aac0e2e273f3f685e6a09f067e29e9eadb2e52d0fe24d417f3d`.

All declare false for paths, pixels, audio, names, identity and editorial
decisions. Unit tests cover sparse timing, availability-filtered candidate
lists, boundary context, exact rebuilding and mutation rejection.

## Limitations and conclusion

The policy is a deterministic POC sampling schedule, not evidence that five
anchors are sufficient for every event type. It currently consumes reaction
events only because Event Timeline v1 does. The packet does not carry motion,
scene-change or dialogue evidence yet. The narrow gate passes: implement a
temporary renderer that resolves the checksummed grid and enforces cleanup;
do not acquire another model first.
