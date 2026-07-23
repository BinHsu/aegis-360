# Apple Vision real-frame gate — 2026-07-23

Status: Observed bootstrap evidence; no backend or projection strategy selected

## Question

Can the already-installed Apple Vision framework produce bounded,
machine-readable candidate evidence from rectilinear views of a verified
benchmark frame, without downloading a model or adding a dependency stack?

## Implementation

`tools/vision_frame_gate.swift` runs three OS-provided requests:

- attention-based saliency;
- objectness-based saliency;
- human rectangles.

`scripts/run_vision_frame_gate.sh` extracts four 640x360 rectilinear horizon
viewports at yaw 0, 90, 180 and -90 degrees with 100-degree horizontal FOV. It
passes the requested source timestamp into the evidence and deletes extracted
PNG frames when the process exits. Evidence and `/usr/bin/time -l` metrics are
written only to the caller-selected output directory.

The JSON uses a job-safe source ID, not the input path. Candidate viewport
boxes are mapped to approximate yaw, pitch and horizontal extent with pinhole
tangent geometry. The result names its adapter/backend/projection provenance
and explicitly reports request errors rather than treating an empty result as
an execution failure.

## Synthetic gate

Command:

```sh
tests/test_vision_frame_gate.sh
```

A generated 640x360 black image with one white rectangle compiled and ran on
Apple Swift 6.3.3. The test verified the schema, three request records,
timestamp, privacy-safe source identity and absence of `/Users/` in JSON.
Candidate count is intentionally not asserted because this fixture does not
establish natural-image model behavior.

Vision emitted `sysctlbyname for kern.hv_vmm_present failed with status -1`
on this execution host, but the process returned success and all request
records were present.

## Real-frame smoke

- Repository base commit: `ce9b700` plus the uncommitted gate implementation
- Machine/OS: reference MacBook Air M4, 16 GB; macOS 26.5.2 (25F84)
- Swift: Apple Swift 6.3.3
- FFmpeg: 8.1.1
- Source: `old_ghost_road_360`, manifest SHA-256
  `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`
- Source timestamp: 30.0 seconds
- Extraction: four 640x360 rectilinear horizon viewports, 100-degree
  horizontal FOV, linear `v360` interpolation
- Network, package and model acquisition: none
- Evidence location: external data root under
  `outputs/vision-frame-gate/old-ghost-road-t30/`; not committed

Observed request runtime for all four viewports was 0.43 seconds with
50,348,032-byte maximum RSS. A separate Swift compile took 0.93 seconds with
183,746,560-byte maximum RSS. These are one-run gate measurements, not
sustained-performance claims, and exclude FFmpeg viewport extraction.

All three request types executed without a reported error on all four
viewports. Attention saliency returned four candidates in total (one per
viewport). Objectness saliency and human rectangles returned zero candidates
at this timestamp. An empty result is neither an API failure nor evidence of
adequate recall.

During integration review, the same versioned runner was repeated at 31.0
seconds into Old Ghost Road with a distinct privacy-safe source ID and output
directory. It completed in 0.35 seconds with 50,561,024-byte peak RSS, again
without request errors. Attention saliency returned four candidates,
objectness returned three, and human rectangles returned zero. The adjacent-
timestamp difference is further evidence that one smoke frame cannot establish
recall, stability, or useful editorial semantics.

## What this unlocks

The native Vision path is executable on a real benchmark frame and can serve
as one adapter candidate in the projection comparison. This does **not**
select Apple Vision as the backend, validate candidate quality, demonstrate
human/event recall, prove execution on GPU/ANE, or select overlapping
viewports as the final projection strategy.

Next evidence must manually review multiple timestamps and events, quantify
recall and duplicate behavior, add spherical cross-viewport deduplication, and
compare against direct ERP inference or another explicitly acquired backend.
