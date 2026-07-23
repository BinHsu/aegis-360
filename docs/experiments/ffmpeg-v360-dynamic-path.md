# FFmpeg v360 dynamic path

Status: In progress

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

### 2026-07-23 timestamped command slice

This run establishes discrete timestamped control and basic synthetic A/V
timing only. It does not establish smooth interpolation, absolute orientation,
real-media sync, performance, memory, thermal behavior, or final-renderer
suitability, so the overall experiment remains **In progress**.

- Environment: same host and FFmpeg 8.1.1 build as the static slice.
- Input: locally generated, static 1024x512 ERP-like grid at 10 fps for 2
  seconds, with a continuous 997 Hz PCM tone at 48 kHz. No external media.
- Control: `sendcmd` steps `yaw` from 0 to 45 degrees at 0.5 s, `pitch` from
  0 to 35 degrees at 1.0 s, and horizontal FOV from 90 to 55 degrees at 1.5 s.
- Render: 640x360 lossless H.264/YUV420P plus AAC in MP4. Lossless encoding
  makes equal-frame assertions meaningful; this is a correctness fixture, not
  the intended delivery bitrate.
- Command: `tests/test_ffmpeg_v360_dynamic.sh`.
- Observed result: PASS. The output had 20 video frames and audio; commands
  changed decoded pixels exactly at frames 5, 10 and 15 (zero-based), frames
  within each constant-pose segment matched, video PTS ran from 0.0 to 1.9 s,
  and both stream durations were within the test's 30 ms A/V tolerance.
- Runtime-control detail: the command target must be `v360` for the default
  filter instance. A probe that targeted only the custom suffix `camera` of
  `v360@camera` returned `Function not implemented` and produced unchanged
  frames. The float options do not accept per-frame expressions such as
  `45*t` in this build.
- Artifacts: generated in a temporary directory and removed by the test.

The verified mechanism implements timestamped **step changes**, not a smooth
camera path. A planner must currently emit dense enough commands (potentially
one per output frame) or another renderer/control mechanism must supply
interpolation. That is the next evidence gate.

### 2026-07-23 dense smooth-path data slice

This slice implements and unit-tests the planner-to-renderer path data. It
does not yet render the dense command stream, so the experiment remains **In
progress**.

- Implementation: dependency-free `src/aegis360/camera_path.py`.
- Sparse yaw/pitch/FOV keyframes are expanded at output-frame timestamps with
  monotone quintic smootherstep interpolation. Each segment has zero endpoint
  velocity and acceleration, does not overshoot its coordinate endpoints, and
  has documented analytic per-coordinate velocity and acceleration bounds.
- Yaw is unwrapped by shortest displacement before interpolation, then wrapped
  back to FFmpeg's degree range only while formatting `v360` commands. Pitch
  is validated within the poles; the implementation explicitly does not claim
  geodesic interpolation or meaningful yaw intent at an exact pole.
- The formatter emits yaw, pitch and horizontal-FOV values for every frame and
  targets the default `v360` filter name established by the prior runtime test.
- A local FFmpeg syntax smoke test also passed with yaw, pitch and FOV emitted
  as three commands at the same timestamp. This checks the formatter's command
  layout, not the continuity of a rendered dense path.
- Command: `python3 -m unittest discover -s tests -v`.
- Observed result: PASS, 19 tests total (7 camera-path tests and 12 geometry
  tests). Coverage includes shortest-path `+179` to `-179` seam crossing,
  exact on-grid keyframe timing, near-pole/FOV no-overshoot behavior, analytic
  derivative bounds, invalid input rejection, degree formatting, and renderer-
  boundary yaw wrapping.

The next gate is to feed this dense command output through FFmpeg and verify
frame-by-frame orientation continuity, command-file semantics and practical
command-stream size on a longer proxy.

### 2026-07-23 multi-segment derivative gate

This slice measures the interpolation function analytically; it does not set
or validate a human comfort threshold.

- Implementation: `segment_limits` now reports exact per-coordinate maximum
  yaw, pitch and horizontal-FOV velocity, acceleration and jerk.
  `keyframe_continuity` reports exact one-sided derivatives at every interior
  keyframe after seam-aware yaw unwrapping.
- Observed property: each independent quintic segment has zero endpoint
  velocity and acceleration, so joins are C2. Endpoint jerk is
  `60 * delta / duration^3`; jerk is generally discontinuous when adjacent
  segment displacement or duration differs.
- Reproducible asymmetric fixture: yaw `0 -> 40 -> 10` degrees at timestamps
  `0, 2, 3` seconds produces left/right yaw jerk of `300` and `-1800`
  degrees/s^3, a `-2100` degrees/s^3 jump. Pitch and FOV jumps are also
  asserted. A symmetric seam-crossing fixture verifies unwrapped yaw can have
  zero jerk jump.
- Scope: these are coordinate-angular derivatives. They do not establish
  perceived comfort, a spherical orientation-space jerk metric, rendered
  frame continuity, or acceptable planner weights.
- Command: `python3 -m unittest discover -s tests -v`.
