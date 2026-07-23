# Apple Vision homographic motion probe

This bounded probe estimates adjacent-frame image motion in an already-flat
video. It uses `VNTrackHomographicImageRegistrationRequest`; it does not
stabilize footage, alter a camera path, or invoke FFmpeg `v360`.

Run:

```sh
scripts/run_vision_motion_probe.sh INPUT_FLAT_VIDEO OUTPUT.json SOURCE_ID START DURATION FPS
```

`SOURCE_ID` must contain only letters, digits, `.`, `_`, `:`, or `-`.
The runner extracts sampled frames into a private temporary directory and
deletes it on exit. The JSON contains timestamps, row-major homographies,
pixel and normalized translation proxies, rotation proxies, determinant
proxies, and aggregate RMS/p95/maximum values. It contains no input path,
pixels, thumbnails, audio, GPS, or identity data.

Translation and rotation values are derived from the upper affine portion of
the homography. The JSON preserves Vision's native matrix convention rather
than claiming one top-left current-to-prior sign rule. The matrix is explicitly
row-major as `[r00,r01,tx,r10,r11,ty,r20,r21,r22]`; the rotation proxy is
`atan2(r10,r00)` in radians. The versioned host calibration fixture establishes
the empirical axis and rotation signs required before correction. These remain
image-registration evidence, not camera-motion ground truth: parallax, rolling
shutter, independently moving objects, and failed registration can contribute
to the measurements.

Synthetic gate:

```sh
tests/test_vision_motion_probe.sh
```

Signed transform and matrix-layout calibration:

```sh
tests/test_vision_motion_calibration.sh
```

This creates two lossless, two-frame flat-video fixtures: known `(+18,+12)`
pixel content translation and known `+4°` clockwise content rotation. In a
restricted sandbox where Vision returns no observations, the test emits an
explicit `SKIP` and directs the same command to be run on the macOS host.

## Host calibration result

The first host calibration failed because the consumer assumed a simple
top-left, current-to-prior sign convention for both translation and rotation.
Inspection of the returned matrices showed that this assumption did not match
Vision's native convention. The probe and calibration assertions were then
changed to preserve and test the empirically observed Vision-native axis and
rotation signs. The translated and rotated fixtures subsequently passed on
the macOS host. This calibrates the correction boundary for these fixtures; it
does not turn registration into camera-motion ground truth.

## Real last-five-second planning result

The calibrated probe and flat-stabilization planner were run at 6 fps over the
last five seconds of the v4 110-degree Old Ghost Road fixed-forward and
auto-directed renders. Evidence and plans are outside Git under the external
artifact root:

- `outputs/auto-directed/old-ghost-road-30s-v1/motion-fixed-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/stabilization-fixed-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/motion-auto-last5-v2.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/stabilization-auto-last5-v2.json`

The fixed-forward plan reports a 120-pixel conservative symmetric overscan
margin, a centered 1680x840 crop and 119.42 pixels maximum corrected-corner
displacement. This is bounded enough to proceed to a five-second
Apple-native post-warp A/B, subject to a rendered blank-edge gate.

The auto-directed plan reports a 360-pixel margin, a centered 1200x360 crop
and 504.55 pixels maximum corrected-corner displacement. That crop discards
two thirds of the 1080-pixel frame height, while the maximum corner motion
also exceeds the reported margin. It is unacceptable as a review candidate.
Do not render the auto-directed A/B from this plan or treat stronger cropping
as a comfort remedy.

The next experiment is therefore only the fixed-forward five-second
Apple-native post-warp A/B at native output resolution, with audio/timestamps
preserved and explicit blank-edge and decodability checks. Its purpose is to
test the calibrated warp direction and bounded crop on real footage; it does
not yet claim viewer-comfort improvement.

## Original ERP source-motion check

The same 25–30 second interval was measured directly from the original
4096x2048 ERP, without `v360` reprojection. All 29 adjacent pairs returned
observations. Rotation-proxy RMS was 0.03538 radians per sampled pair, p95 was
0.07566 and the maximum was 0.13231; translation RMS was 107.04 source
pixels. This confirms substantial motion exists in the source imagery before
flat reprojection.

The source ERP and fixed-static flat view shared a notable rotation peak at
28.17 seconds, but their full absolute-rotation correlation was weak. Their
projection, visible content, seam behavior and parallax differ, so their
homographies are not numerically interchangeable. The supported conclusion is
limited to source-motion presence: `v360` may alter its perceptual expression
but did not originate it.

## First native post-warp result

The fixed-forward plan was rendered over the five-second interval with the
Apple-native Core Image path. The output decoded at 1920x1080 for five seconds,
retained audio, and passed the renderer's synthetic blank-edge contract.
However, the same translation-only shake probe did not improve: median global
step rose from 2.83 to 3.61 proxy pixels and p95 vector change rose from 5.25
to 12.12. This candidate is rejected and must not be presented as stabilized
review media.

The failure may come from correction direction, 6-to-25 fps interpolation,
trajectory smoothing, crop magnification, registration/parallax, or the
translation-only evaluator's limitations. A known-motion end-to-end
stabilization fixture must show reduced translation, rotation and vector
change before another real render.
