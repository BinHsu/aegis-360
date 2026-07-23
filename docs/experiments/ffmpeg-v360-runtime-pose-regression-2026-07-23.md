# FFmpeg v360 runtime-pose regression

Status: Reproduced on synthetic input

## Question

Does the installed FFmpeg `v360` filter treat repeated runtime yaw commands as
absolute orientations, as required when the planner emits a dense absolute
camera path?

## Environment

- Run date: 2026-07-23.
- Host: Apple Silicon MacBook Air M4, 16 GB unified memory.
- FFmpeg: Homebrew FFmpeg 8.1.1, built with Apple clang 21.0.0.
- Input: repository-generated, static 1024x512 asymmetric ERP fixture at
  10 fps for 2 seconds; FFV1/YUV444P; no external media, model, or network.
- Output: 640x360 flat projection, linear interpolation, 90-degree horizontal
  FOV, FFV1. Lossless output makes decoded-frame hashes comparable.

## Reproduction

Run:

```sh
tests/test_ffmpeg_v360_runtime_pose_regression.sh
```

The executable test renders three variants:

1. Static `yaw=45`.
2. A single `sendcmd` update to `yaw=45` at `t=0`, starting from static
   `yaw=0`.
3. A planner-like sequence of requested absolute yaws: `0` at 0.0 s, `45` at
   0.5 s, `-30` at 1.0 s, and `45` again at 1.5 s.

Every decoded frame from variant 2 matched variant 1. In variant 3, frames
0.5--0.9 s at the first requested `yaw=45` also matched the static `yaw=45`
pose. Frames 1.5--1.9 s, after returning to the same requested `yaw=45`,
produced a different decoded-frame hash from both the static pose and the first
runtime visit.

Observed result: PASS. The behavior reproduces deterministically with the
synthetic asymmetric fixture and requires no Old Ghost Road footage.

## Interpretation

The installed build advertises timeline support for `yaw`, accepts each
command, and visibly updates the projection. A one-command `t=0` probe is
therefore insufficient evidence that a sequence of absolute planner
orientations renders as those absolute poses. On this build, runtime yaw output
is path-dependent across multiple updates.

This experiment proves pixel inequality, not the internal cause. In
particular, it does not claim that every FFmpeg version accumulates yaw, nor
that pitch and FOV have identical behavior. It also does not measure angular
error, A/V sync, performance, thermal behavior, or subjective motion quality.

## Consequence

Do not treat dense absolute `sendcmd` values as a correct final camera-path
renderer on the installed FFmpeg 8.1.1 build. Keep the executable regression
as an environment-specific semantics gate. A replacement control scheme or
renderer must compare repeated requested poses against equivalent static
renders before it can unlock dynamic-path correctness.
