# FFmpeg v360 dynamic path

Status: Planned

## Question

Can the installed FFmpeg apply a timestamped yaw/pitch/FOV path correctly and
quickly enough for POC proxy previews and an occasional final render?

## Decision unlocked

Choose initial preview/final renderer and identify whether a Metal spike is
necessary for time-to-evidence.

## Inputs and variants

Use geometry fixtures plus short licensed benchmark excerpts. Compare static
poses, runtime/sendcmd path updates, continuous seam crossing, explicit cuts,
interpolation modes and CPU versus available VideoToolbox decode/encode where
compatible.

## Procedure

Capture exact commands/filter help/version; render paths with known timestamps;
inspect frame orientation, black borders, duration, frame count and A/V sync;
then measure cold and repeated proxy/full-resolution excerpts.

## Metrics and acceptance criteria

Record orientation/path error, duration/frame-count error, A/V offset, FPS,
wall time, peak RSS, swap, CPU/energy and command-file size. Accept for the POC
if semantics match geometry tests, output has no projection gaps or material
sync drift, proxy preview iteration is practical, and one final render can
complete within a documented budget on the reference machine. The budget must
be fixed before timed runs.

## Run record

### 2026-07-23 static capability slice

This run deliberately covers only static reprojection. It does not establish
the semantics, continuity, or performance of timestamped yaw/pitch/FOV
updates, so the overall experiment remains **Planned**.

- Host: Apple Silicon MacBook Air M4, 16 GB unified memory.
- FFmpeg/ffprobe: Homebrew `/opt/homebrew/bin`, FFmpeg 8.1.1, built with Apple
  clang 21.0.0; the build advertises `v360`, slice threading, libx264 and
  VideoToolbox.
- Input: locally generated 1024x512, 10 fps, 2 second FFV1/YUV444P synthetic
  grid with five colored markers; no external media and no audio.
- Render: equirectangular to 640x360 flat projection, bilinear interpolation,
  90 degree horizontal FOV, yaw 0 and yaw 90, H.264/YUV420P output.
- Command: `tests/test_ffmpeg_v360_static.sh` (the test invokes the two scripts
  under `scripts/`).
- Observed result: PASS. The fixture contained 20 frames; both outputs
  contained 20 frames at 640x360, decoded without FFmpeg errors, and the final
  decoded-frame hashes differed between yaw 0 and yaw 90.
- Artifacts: generated in a temporary directory and removed by the test.

This verifies that the installed build can execute the repository's minimal
static ERP-to-flat path and that changing static yaw changes pixels. It does
not yet verify absolute orientation, seam behavior, black-border absence,
audio/timestamp preservation, runtime/sendcmd control, performance, memory,
thermal behavior, or suitability as the final renderer.
