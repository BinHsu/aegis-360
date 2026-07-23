# Spherical geometry

Status: Active design; static FFmpeg renderer convention validated

## Coordinate contract

Use radians internally. For an ERP image of width `W` and height `H`, pixel
centers are mapped by the initial convention:

```text
u = (x + 0.5) / W
v = (y + 0.5) / H
yaw   = 2*pi*u - pi
pitch = pi/2 - pi*v
```

Yaw wraps modulo `2*pi`; pitch is clamped to `[-pi/2, pi/2]`. Camera poses and
observations must declare their coordinate convention and not rely on FFmpeg
sign conventions implicitly. The geometry experiment must establish the exact
conversion to renderer yaw/pitch/roll.

For the installed FFmpeg 8.1.1 `v360` filter with equirectangular input, the
validated static conversion is direct after converting radians to degrees:
positive internal yaw maps to positive `yaw`, positive internal pitch maps to
positive `pitch`, and horizontal FOV maps to `h_fov`. Both `+180` and `-180`
center the ERP seam. This is a tested adapter contract, not an assumption that
all renderers use the same signs. Roll and timestamped command semantics remain
separate validation work.

## Required operations

- pixel/ERP direction conversion in both directions;
- great-circle angular distance using numerically stable vector operations;
- circular mean and seam-aware extents;
- yaw unwrapping relative to the prior pose;
- rectilinear ray generation for horizontal/vertical FOV;
- spherical interpolation and bounded camera-path derivatives;
- seam-aware observation and candidate-shot representation.

A box center in ERP coordinates is only a proposal. Near the seam or poles,
candidate aim points should be derived from spherical samples or masks when
available. Projection distortion must not be treated as ordinary planar area.

## Camera continuity

Paths are represented as timestamps plus unwrapped yaw, pitch, FOV and cut
markers. Interpolation must not take the long way around the seam. Continuous
segments are evaluated for angular velocity, acceleration and jerk; a cut
starts a new segment.

## Acceptance criteria

- Synthetic cardinal markers round-trip within a documented sub-pixel/angular
  tolerance.
- A target crossing `+pi/-pi` produces a short continuous rotation, not a full
  revolution.
- Pole-adjacent and seam-straddling fixtures contain no NaN/Inf and select the
  intended direction.
- FOV and orientation agree with the installed FFmpeg `v360` reference on
  generated grids.

Exact tolerances are established in `docs/experiments/geometry-validation.md`
before becoming regression requirements.
