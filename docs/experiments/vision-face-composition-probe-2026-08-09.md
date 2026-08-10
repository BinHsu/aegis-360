# Vision face composition probe — 2026-08-09

Status: Conservative group composition accepted by owner

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
floor. Its body geometry is yaw 54.083 degrees and pitch -25.278 degrees, with
51.474 degrees required horizontal coverage. The result carries no cross-time
member IDs and uses `simultaneous_group_geometry_nonidentity` provenance. The
renderer independently retains its 110-degree minimum FOV.

## Proposal/render follow-up

An atomic, path-free proposal artifact now separates geometry generation from
human/local-VLM selection. The selected `group:window:1` proposal is then
adapted into the unchanged greedy planner and atomic render bundle.

The first proposal copied the only detected face pitch (-6.124 degrees) into
the group camera pose. Its render passed mechanical checks but agent contact-
sheet review rejected it: the single face pulled the whole group too high and
crowded another visible member against the lower edge. It was not sent to the
owner.

A second immutable proposal limits face-derived pitch correction to 5 degrees.
It renders at yaw 54.083 degrees, pitch -20.278 degrees and HFOV 110 degrees.
Both peers are H.264 High, yuv420p, 1920x1080 at 25 fps; the group is selected
16/16 times and the maximum fixed/auto pose difference is 56.615 degrees.
Agent inspection finds a clear directing difference, all three visible heads
retained, and no obvious blur, blocking or seam defect. The nearby cap-wearing
person is partially cropped below the torso.

On 2026-08-11 the owner accepted this result for the stated gate: the output
successfully captures the two people in conversation. This acceptance is for
group framing only. It does not establish active-speaker recognition, speaker
identity, automatic context classification, subject switching or longer-window
tracking.

The 5-degree limit has status `tunable_poc_guard_not_validated_default`. This
four-second human-selected context test does not validate automated scene
classification, active-speaker identity, longer tracking or a universal
composition threshold.
