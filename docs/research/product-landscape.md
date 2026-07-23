# Product landscape

Verified: 2026-07-23

## Product question

aegis-360 is not intended to reproduce a manual target-lock workflow. Its
hypothesis is that an offline desktop system can inspect a complete 360 video,
choose what an ordinary first-time viewer is likely to care about, plan a
coherent virtual camera, and export a conventional flat video without requiring
the user to identify a subject.

## Capability layers

1. Detection: find people, objects, actions, and regions.
2. Tracking: maintain identities through time and spherical seam crossings.
3. Subject/event selection: decide what deserves attention.
4. Auto-directing: choose shot, viewpoint, FOV, dwell, pan, and cut behavior.
5. Auto-editing: retain, shorten, order, and style clips.

Comparisons must name the layer being compared. “AI tracking” does not imply
automatic subject selection, and automatic reframing does not imply highlight
editing.

## Confirmed landscape observations

- Insta360 documents Deep Track separately from Auto Frame and Auto Edit.
  [Deep Track](https://onlinemanual.insta360.com/studio/en-us/operation-guide/edit-function/deep-tracking-function),
  [Auto Edit](https://onlinemanual.insta360.com/app/en-us/operation-tutorial/edit-function/auto-edit)
- Insta360's Auto Edit description includes smart framing, clip selection,
  360-camera movement, scene recognition, and music matching.
- Automatic reframing is established prior art, including the 2017 research
  system *Making 360° Video Watchable in 2D*.
- FFmpeg provides projection conversion primitives including `v360`; this is a
  component, not an auto-director.

## Unknowns that require experiments

- Exact feature availability for non-Insta360 equirectangular files in current
  Studio and App versions.
- Whether missing camera metadata, proxy/analysis files, supported-mode flags,
  account state, or product-surface differences explain any particular failed
  Auto Edit attempt.
- Relative quality of vendor auto-editing across generic everyday, first-person
  sports, group interaction, and low-event footage.
- Whether aegis-360's explainable global planner yields a meaningful viewer
  preference advantage.

## Defensible positioning

Avoid “no competitor can do this” and “first automatic 360 editor.” The claim to
test is narrower:

> Offline, account-free, camera-agnostic automatic subject/event selection and
> virtual-camera planning from standard equirectangular footage, with an
> inspectable decision trace.

The POC proves Full Story first: preserve chronology and most content while
choosing viewpoints. Highlights are a later policy over the same interest and
event evidence.
