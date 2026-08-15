# Event timeline v1

Status: Executed on 2026-08-16

## Question and decision unlocked

Can existing low-cost reaction evidence be normalized into one immutable,
privacy-safe whole-video timeline without importing the owner's editorial
answers? A pass unlocks sparse before/during/after review packets under ADR
0010. It does not unlock a cut, select a model or establish who reacted.

## Contract

`aegis360.event-timeline.v1` binds the exact SHA-256 values of the context-view
grid, editorial roles, reaction intervals and candidate-scoped availability.
It derives stable event IDs, clips events to the declared analysis window and
retains both the unclipped audio-event boundary and the proposed view's actual
availability intersection.

The validator reconstructs the complete document from those four inputs.
Added decisions, changed candidates, geometry or altered input checksums fail
closed. Durable output contains no source path, pixels, audio, names or
identity. V1 emits reaction candidates only; it is not yet a complete story
timeline.

## Environment and procedure

- Repository baseline: `267d5b0` plus the implementation under test.
- Hardware: fanless Apple Silicon M4 MacBook Air, 16 GB unified memory.
- OS: macOS 26.5.2 (25F84).
- FFmpeg: 8.1.1; no decoding or rendering was required for this derivation.
- Models: none.
- Inputs: previously validated, checksummed grid, role, reaction-interval and
  candidate-availability JSON artifacts for Gaudeamus and Hundra.
- Command: `scripts/build_event_timeline.py GRID ROLES REACTIONS AVAILABILITY OUTPUT`.

The command reads all four inputs before construction, binds their raw-byte
checksums, writes through a same-directory temporary file, refuses overwrite
and prints only the event count.

## Results

Gaudeamus emitted two events:

- 9.0–15.0 seconds: the proposed audience view is unavailable at onset and
  overlaps only 11.5–15.0.
- 109.5–124.5 seconds: the proposed view is available at onset and overlaps
  109.5–119.0.

Hundra emitted one event at 217.5–226.5 seconds. Its proposed audience view is
available for the full event. This is deliberately still a candidate: the
owner's prior rejection is absent from the timeline.

External artifacts, never committed:

- `outputs/event-timelines/gaudeamus-reaction-v1/timeline.json`, SHA-256
  `d545ee8e68649bea0d2da97d2b413aea2f91a21153d4cb372cd015546dac8314`.
- `outputs/event-timelines/hundra-reaction-v1/timeline.json`, SHA-256
  `1bdf127495d2e618cd3df95f70decc7c490193593a124f53b227b5d1964ac3a3`.

Both artifacts pass the closed privacy declaration and a scalar-string scan
for absolute paths. Unit tests cover clipping, original event timing, onset
availability, exact rebuilding and rejection of injected decisions, swapped
candidates and altered hashes.

## Limitations and conclusion

The three events reuse one reaction-evidence family and do not prove event
recall, story quality or model accuracy. Role and availability evidence remain
upstream declarations. The result passes its narrower gate: it preserves the
information needed to schedule sparse semantic review while keeping benchmark
answers out of the product input. Build Event Review Packet v1 next; do not
acquire or tune another VLM first.
