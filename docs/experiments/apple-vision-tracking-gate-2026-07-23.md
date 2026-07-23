# Apple Vision short-sequence tracking gate — 2026-07-23

Status: Real smoke observed; synthetic fixture produced a negative result

## Question

Can the installed Apple Vision framework maintain one externally initialized
box over a bounded frame sequence and emit privacy-safe continuity evidence
that can later sit behind the tracker adapter?

This follows the project owner's qualitative acceptance of the displayed
single-frame box localization. It does not revisit whether those boxes select
interesting content.

## Implementation

`tools/vision_tracking_gate.swift` uses `VNSequenceRequestHandler` and
`VNTrackObjectRequest` revision 1 at the accurate tracking level. The stable
runner is:

```sh
scripts/run_vision_tracking_gate.sh \
  INPUT_VIDEO OUTPUT_DIR SOURCE_ID TRACK_ID \
  START DURATION FPS VIEWPORT_YAW BOX_X BOX_Y BOX_W BOX_H
```

The runner extracts a bounded 640x360, 100-degree rectilinear sequence into a
temporary directory, compiles and runs the native probe, then deletes the
frames. It refuses an existing output directory. JSON contains only safe IDs,
numeric timestamps, normalized boxes, approximate spherical centers, center
steps, confidence, lost/error state and aggregate counts. It contains no media
path, frame pixels, face, embedding or identity label.

Confidence is retained only as perception evidence. It is not transformed
into editorial interest.

## Synthetic moving-box gate

`tests/test_vision_tracking_gate.sh` generates six frames containing a moving,
textured rectangle near a wrapped viewport heading. It verifies compilation,
schema, privacy, overwrite/input safeguards and either:

- returned tracks with bounded spherical steps and seam-aware wrapping; or
- an explicit `no_tracking_observations` negative outcome.

On this run the synthetic fixture returned no tracking observations. The gate
therefore does not claim synthetic identity or seam continuity. This negative
result is retained because a simple rendered rectangle is not evidence that
the tracker handles natural image structure.

## Old Ghost Road real smoke

- Machine/OS: reference MacBook Air M4, 16 GB; macOS 26.5.2 (25F84)
- Swift: Apple Swift 6.3.3
- Source: `old_ghost_road_360`, verified manifest asset
- Source interval: 15.0–17.0 seconds
- Sampling: 2 fps, four frames
- Viewport: yaw 0 degrees, pitch 0 degrees, 100-degree horizontal FOV
- Initial box: accepted attention-saliency box from the existing 15-second
  review sample
- Network, package and model acquisition: none
- Evidence: external data root under
  `outputs/vision-tracking-gate/old-ghost-road-t15-yaw0-v2/`; not committed

Observed:

| Metric | Value |
| --- | ---: |
| requested frames | 4 |
| tracked frames | 4 |
| lost/error frames | 0 / 0 |
| persistence ratio | 1.0 |
| maximum spherical center step | 3.341532 degrees |
| wrapped seam crossings | 0 |
| probe elapsed time | 0.39 seconds |
| maximum resident set size | 24,068,096 bytes |
| reported peak memory footprint | 47,366,768 bytes |

The JSON scan found no `/Users/`, `/Volumes/`, face/identity field or interest
score.

## Interpretation and limitations

This establishes that `VNTrackObjectRequest` can return a continuous box on
one four-frame natural-video smoke sequence on the reference machine. It does
not establish benchmark-wide track persistence, identity-switch rate, correct
subject identity, seam handoff, acceptable lost-track grace, or tracking
quality. The initial region is externally supplied and large; the result is
not a detector evaluation.

The synthetic/real difference also means the tracker must preserve explicit
lost/error outcomes rather than treating API execution as successful
tracking. Next evidence should use several manually inspectable short clips,
include a target that approaches a viewport boundary, and compare track
continuity with a reviewed reference before this becomes an adapter choice.
