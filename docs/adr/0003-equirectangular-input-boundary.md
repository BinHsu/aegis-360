# 0003: Start from monoscopic equirectangular video

Status: Accepted

## Context

Native camera formats add vendor-specific containers, projection layouts,
calibration, stabilization, and telemetry before the auto-directing question
can be tested. Conversely, a 2:1 aspect ratio alone does not prove a valid
equirectangular projection, and benchmark footage includes both MP4 and WebM
with varying dimensions.

## Decision

The POC accepts already-stitched, monoscopic equirectangular video decodable by
FFmpeg. Initially guaranteed combinations are MP4 with H.264/H.265 and WebM
with VP8/VP9. Validation must inspect streams and available spherical metadata,
must not infer projection from aspect ratio alone, and may provide an explicit
user override for known inputs.

Native GoPro `.360`, Insta360 `.insv`, lens stitching/de-stitching, and vendor
projection conversion are outside the POC boundary.

## Consequences

- Camera exports may be used, but stabilization, horizon leveling, telemetry
  removal, color handling, frame rate, and timestamps are not assumed; they
  must be inspected or preserved appropriately.
- A non-exact 2:1 input is not rejected solely for its dimensions.
- Direct native-camera support requires future evidence and a separate
  decision; it is not described as merely de-stitching.
- Input normalization remains distinct from auto-directing.
