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
the homography. They are evidence of image registration, not camera-motion
ground truth: parallax, rolling shutter, independently moving objects, and
failed registration can contribute to the measurements. Treat signed
direction as uncalibrated until the synthetic gate returns observations on an
unrestricted host; the raw row-major matrix is retained so that calibration
does not discard evidence.

Synthetic gate:

```sh
tests/test_vision_motion_probe.sh
```
