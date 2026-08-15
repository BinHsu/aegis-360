# Transient event review media

Status: Executed on 2026-08-16

## Question

Can an Event Review Packet be resolved to actual rectilinear frames for a
replaceable adapter without making those frames durable or allowing the
adapter to invent camera geometry? A pass unlocks the closed semantic-output
contract. It does not select or validate a model.

## Implementation boundary

`run_event_review_adapter.py` accepts source video plus exact timeline, grid
and packet artifacts. It validates packet lineage, resolves candidate IDs to
grid-owned yaw/pitch/FOV and builds at most ten 384x216 PNG jobs. Each job is a
single silent FFmpeg `v360` projection. The adapter receives a relative-file
index through `AEGIS_REVIEW_MEDIA_INDEX`; the source path and geometry are not
placed in that index.

Rendering and adapter execution occur inside one Python `TemporaryDirectory`.
The runner invokes an argv array without a shell and returns the adapter exit
code. Normal return, adapter failure and Python exceptions all exit the same
cleanup scope. Audio is never passed.

## Real run

Environment: fanless M4 MacBook Air, 16 GB unified memory; macOS 26.5.2
(25F84); FFmpeg 8.1.1; no model or network access.

The Gaudeamus opening packet resolved to seven nonempty PNG files: one current
view at before, early and after anchors, plus current/proposed pairs at the
midpoint and late anchors. A diagnostic adapter loaded the transient index,
matched all 7 files and checked nonzero byte size. End-to-end elapsed time was
0.51 seconds. The reported temporary directory no longer existed after runner
exit.

An initial diagnostic assertion expected six files because of a manual
counting mistake and returned failure. The runner propagated that failure and
cleaned the directory. Recounting from the manifest established seven as the
correct value; no product code was weakened to satisfy the mistaken assertion.

No peak-memory claim is made: `/usr/bin/time -lp` emitted a restricted
`sysctl kern.clockrate` warning and did not provide a usable memory result.

## Verification, limitations and conclusion

Unit tests cover job bounds, candidate resolution, transient index contents
and fail-closed invented candidates. A source-contract test requires temporary
directory use, one-frame silent extraction, index handoff and no `shell=True`.

This smoke run covers one source/event and diagnostic adapter. Per-frame
FFmpeg starts are acceptable for the bounded POC but are not a throughput
claim. The adapter can still read temporary paths by design; cleanup, not path
secrecy, is the control. The gate passes. Define a checksummed, closed
event-semantic-evidence schema with explicit abstention next; do not let it
emit candidates, geometry or renderer commands.
