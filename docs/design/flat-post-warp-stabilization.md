# Flat-video post-warp stabilization

Status: minimal synthetic implementation; not validated on benchmark footage

`scripts/plan_flat_stabilization.py` consumes schema-version-1 output from
`vision_motion_probe`. It accumulates adjacent registrations, projects each
homography to its nearest orientation-preserving similarity, smooths the
cumulative path with a bounded Gaussian window, and emits a correction
homography for every sampled timestamp.

Example:

```sh
PYTHONPATH=src python3 scripts/plan_flat_stabilization.py \
  motion-evidence.json stabilization.json \
  --measurement-direction previous_to_current \
  --smoothing-radius 0.5
```

The measurement direction is mandatory because the existing Vision probe has
not yet calibrated its signed transform direction on a known translated
fixture. Missing/error observations are held at identity; production use
should instead add confidence gating and bounded interpolation.

The output records:

- raw and smoothed cumulative `(tx, ty, angle, logScale)` paths;
- a row-major source-pixel correction homography mapping raw to stabilized
  frame coordinates;
- transformed source corners for each frame;
- maximum corner displacement and a conservative centered crop heuristic.

The crop value is planning evidence, not a proof that every rotated
quadrilateral covers the crop. A real render gate must check blank pixels.

## Renderer boundary

The installed FFmpeg `perspective` filter can evaluate expressions per frame,
but its corner options do not advertise runtime-command support. Encoding an
arbitrary sampled path as one very large expression is fragile and is not the
chosen 5-second A/B path.

The shortest Apple-native renderer is an `AVAssetReader` /
`AVAssetWriterInputPixelBufferAdaptor` loop with a `CIContext`. For each video
PTS it interpolates the neighboring correction matrices, applies
`CIImage.transformed(by:)` (all current corrections are similarities), scales
to cover the planned crop, crops to the requested output extent, and renders
into the writer pixel buffer. Audio can be copied through a separate
reader/writer input. If projective corrections are later retained, replace
the affine call with `CIPerspectiveTransform` using the four emitted corrected
source corners; the planner/renderer JSON boundary remains unchanged.

Before a real A/B, calibrate Vision direction with a translated synthetic
fixture, select a crop/zoom policy, and add an output blank-edge gate.
