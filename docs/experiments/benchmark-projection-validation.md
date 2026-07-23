# Benchmark projection validation

Status: Executed on 2026-07-23; two assets accepted, one gated

## Question and decision rule

Can each downloaded benchmark be treated as a monoscopic equirectangular
source by the POC? A 2:1 frame is neither necessary nor sufficient evidence.
Acceptance requires mutually consistent source description, stream/container
inspection, and manual inspection of multiple ERP samples reprojected toward
four equatorial headings and both poles. A missing authoritative container
tag is recorded rather than silently invented.

## Reproduction

Run the following separately for each ID. The command reads originals and
writes low-resolution evidence outside Git.

```sh
AEGIS_DATA_DIR=/path/to/data scripts/inspect_benchmark_projection.sh ASSET_ID
```

The inspected IDs were `bellpuig_onboard_360`, `old_ghost_road_360`, and
`skiing_may_2019_360`. Samples were taken at 5 seconds, half duration, and
5 seconds before the end. Each sample produced the stored ERP frame plus
FFmpeg `v360` views at yaw 0, +90, 180 and -90 degrees and pitch +90 and -90
degrees. The evidence frames remain local external data and are not published.

Environment: macOS on the reference M4 MacBook Air; FFmpeg/ffprobe 8.1.1.

## Source and container evidence

The Wikimedia Commons API categorized all three source pages as
`360-degree videos`. The descriptions identify on-board motocross, a 360 New
Zealand mountain-bike trip, and 360 skiing respectively. Commons media
metadata reports ordinary WebM video/audio properties, but does not state an
equirectangular projection layout.

Local `ffprobe` likewise found no authoritative spherical projection side
data. Bellpuig reports only a `Stereo 3D` side-data entry whose type is `2D`;
that establishes monoscopic packing, not projection. Therefore Commons labels
and visual evidence are supporting evidence, not substitutes for projection
metadata.

## Results

### Old Ghost Road

Accepted as monoscopic ERP for the POC. The VP8 stream is 4096x2048, SAR 1:1.
Across the three timestamps, the stored frames have the expected latitude
stretch and the six rectilinear views form coherent directions, including
plausible sky/ground at the poles. No black projection gaps were observed.
The source/category evidence independently describes it as 360 video.

### 360 Skiing May 2019

Accepted as monoscopic ERP for the POC. The 10-bit VP9 stream is 5120x2560,
SAR 1:1. Across the three timestamps, terrain and people remain coherent in
the equatorial views and the pole views converge to plausible sky and the
camera/mount or snow. No black projection gaps were observed. The
source/category evidence independently describes it as 360 video.

### Bellpuig on-board 360

Confirmed as monoscopic 360 content laid out in an ERP-like image, but **not
accepted yet as geometry-accurate full ERP input**. Its VP9 stream is
3840x2048 with SAR 1:1 and DAR 15:8. `v360` produces visually plausible views
at the sampled headings and poles, and the Commons page calls it 360 video,
but neither the WebM nor Commons metadata explains whether the non-2:1 stored
frame is horizontally cropped, non-uniformly rescaled, or uses another
normalization. Treating its width as exactly 360 degrees would choose one of
those interpretations without evidence.

Gate: identify an authoritative upstream projection/crop statement, compare
against an upstream master with known geometry, or manually label seam and
known-angle landmarks well enough to select and record a normalization. Until
then the validator must require an explicit projection override and the asset
must not be used for spherical-error ground truth. It may still be useful for
qualitative robustness testing if the ambiguity is disclosed.

## Limits

This validation establishes a justified input interpretation for two files;
it does not establish stitching quality, horizon leveling, stabilization,
angular calibration, audio/content publication rights, or suitability as
ground truth. Visual inspection is reproducible but human-reviewed, so a
future input validator must preserve `verified`, `override-required`, and
`unknown` as distinct states.
