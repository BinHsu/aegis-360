# 0009: Bound detector edge repair to one source pixel

Status: Accepted

## Context

Object detectors regress boxes in continuous coordinates and may return an
otherwise useful box fractionally outside the input image. YOLOX 0.3.0
postprocessing converts center boxes to corners and applies NMS without
clipping inference boxes to the image. Rejecting every fractional overflow
can therefore discard valid class/region evidence, while unconditional
clipping can hide malformed geometry.

On the 416x416 Old Ghost Road viewport at t62, the accepted bicycle box
extends 0.0022615 normalized units, or 0.9408 source pixels, below the image.
Clipping that edge moves the box center by 0.0011308 normalized units, about
0.113 degrees for the square 100-degree viewport. The resulting refresh is
compatible with the live Vision bicycle region but does not establish
identity.

## Decision

Detector adapters may offer an explicit, versioned edge-repair policy capped
at one source pixel per axis. The tolerance is converted independently using
the actual viewport width and height. Only an edge outside the viewport by no
more than that bound may be clamped to the boundary.

Zero tolerance remains the default. A nonzero policy requires positive source
dimensions and explicit caller selection. Invalid dimensions, non-finite
values, non-positive boxes, origins outside the viewport, or overflow greater
than one source pixel fail closed.

Edge repair changes geometry only. It cannot promote detector confidence,
semantic identity, track identity, or editorial persistence.

## Consequences

- Runtime traces must record which versioned policy was selected.
- Tests must cover strict rejection, accepted subpixel overflow, rejection
  beyond one pixel, and missing dimensions.
- A later detector or coordinate convention may use strict zero tolerance or
  supersede this ADR with measured evidence.
- This policy does not repair boxes whose top or left origin is outside the
  viewport; such cases remain invalid rather than being silently reshaped.
