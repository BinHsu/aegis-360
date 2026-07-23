# Fixed-forward baseline

Status: Executable baseline; one short real-media smoke run observed

## Purpose

Provide the non-adaptive control required by ADR 0007. The virtual camera uses
one yaw, pitch and horizontal FOV for the full selected segment. This is a
rendering control, not evidence that the input projection is valid or that the
chosen direction is useful to a viewer.

## Reproduction

The renderer requires explicit input and output paths. The example keeps media
and generated output under the ignored external data root:

```sh
export AEGIS_DATA_DIR=/path/to/aegis-360-items
mkdir -p "$AEGIS_DATA_DIR/outputs/fixed-forward"
scripts/render_fixed_forward_baseline.sh \
  "$AEGIS_DATA_DIR/benchmarks/originals/bellpuig_onboard_360.webm" \
  "$AEGIS_DATA_DIR/outputs/fixed-forward/bellpuig-0000-0010-yaw0.mp4" \
  0 10 0 0 90 640 360
```

The output path must not already exist. The renderer normalizes the selected
segment to PTS zero, retains source cadence and A/V offset, reprojects video
with FFmpeg `v360`, and transcodes benchmark audio to AAC for MP4. It does not
download, publish or implicitly select media.

Synthetic regression:

```sh
tests/test_fixed_forward_baseline.sh
```

## Observed run: Bellpuig 0–10 seconds

- Date: 2026-07-23
- Host: Apple arm64, macOS 26.5.2 (25F84)
- FFmpeg: 8.1.1, Apple clang 21.0.0, libx264 enabled
- Input manifest ID: `bellpuig_onboard_360`
- Segment: start 0 s, requested duration 10 s
- Pose: yaw 0°, pitch 0°, horizontal FOV 90°
- Output: 640x360 H.264 at 24000/1001 fps; AAC 48 kHz stereo
- Output timing: video starts 0.000 s and lasts 10.010 s; audio starts 0.000 s
  and lasts 9.979 s; container lasts 10.010 s
- Output size: 776255 bytes
- Output SHA-256:
  `10786f32a8d35bf3974f43354627f8c05cc5c283c8203c2cbb107a26e397b9b7`
- Decode validation: FFmpeg decoded the complete generated file without an
  error
- Wall time, RSS, swap and thermal state: not captured; this is not a
  performance run

No quality, correct-forward-direction or correct-projection conclusion follows
from this smoke run. Bellpuig projection validation remains a separate gate.
