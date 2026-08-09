# Vision face composition probe — 2026-08-09

Status: Face anchor is stable; single-face framing is rejected

## Question

Can an OS-provided face rectangle correct the whole-body person box's vertical
composition on the owner-rejected Old Ghost Road 68.5–72.5 second excerpt?
This is a visibility and geometry probe, not active-speaker recognition.

## Method

`VNDetectFaceRectanglesRequest` was added to the existing path-free Vision
frame gate. The bounded sequence runner sampled four equatorial 100-degree
viewports at 4 fps for four seconds. Viewport PNGs existed only in a temporary
directory and were deleted after each sample. No model was downloaded.

## Result

All 64 face requests succeeded. Forty-eight view/timestamp rows contained no
face; the right viewport contained exactly one face at every one of 16
timestamps. Its spherical center stayed near yaw 61.0–61.5 degrees and pitch
-5.4 to -6.4 degrees, with about 6.8–7.7 degrees horizontal extent.

The previously selected whole-body track stayed near yaw 60.1 degrees and
pitch -28.3 degrees. The 22-degree vertical disagreement explains the owner's
instruction to move the auto view upward. Face evidence is useful as a
composition anchor.

It does not solve the directing problem. The owner sees two people with moving
mouths, while the detector finds only one face. Side pose, occlusion, scale or
headwear can make a member of the same interaction group unavailable to the
face request. A camera candidate centered or cropped from one detected face
could therefore exclude the group and is rejected.

## Decision

- Retain face position as optional composition evidence.
- Generate conversation/group candidates from person or upper-body coverage;
  detected faces may shift the group's visual center upward.
- Reject a face-based candidate that excludes another visible member of the
  same interaction group.
- Mouth motion alone is not speaker identity. A short-window VLM may classify
  scene context, while geometry and the planner remain deterministic.
- If semantic evidence is uncertain, prefer a group view over guessing one
  active speaker.

External evidence:
`outputs/vision-face-sequence/old-ghost-road-t68p5-4s-4fps-four-view-v1/evidence.json`

The JSON is path-free and contains no pixels, embeddings, names or identity
claims. The four-second result does not establish recall on other poses,
scenes, cameras or benchmarks.

## Group-geometry follow-up

Simultaneous spherical person detections form a containable two-person group
at 8/16 timestamps. Those observations are stable near yaw 53.9–54.4 degrees
and whole-body pitch -25.1 to -25.4 degrees. Applying the compatible face only
as a bounded vertical anchor moves pitch to -5.4 to -6.4 degrees while leaving
member coverage, yaw and FOV unchanged. This converges the owner's two framing
instructions on one group direction.

Half the samples lack the second person detection, so per-frame group presence
would flicker. Do not render that directly. A window-level conversation/group
decision must hold the candidate across bounded detector misses; the eight
observed group geometries can provide its robust static pose without claiming
member identity.

The bounded window aggregator accepts the 8/16 ratio at its inclusive 0.5
floor. It produces yaw 54.083 degrees, pitch -6.124 degrees and 51.474 degrees
required horizontal coverage. The result carries no cross-time member IDs and
uses `simultaneous_group_geometry_nonidentity` provenance. The renderer's
existing minimum FOV remains a separate comfort/framing guard.
