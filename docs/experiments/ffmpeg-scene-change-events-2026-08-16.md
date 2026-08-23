# FFmpeg scene-change events

Status: Partially executed on 2026-08-16

## Question

Can a cheap proxy signal add non-audio whole-video boundaries to sparse
semantic review without pretending to measure importance? A pass unlocks
scene-change candidates for a future multi-signal timeline. It does not select
a view or establish that a boundary is interesting.

## Protocol

FFmpeg 8.1.1 decodes locally, samples at 2 fps, scales to 320 pixels wide and
emits frames with `scene > 0.25`. The privacy-safe raw artifact stores timestamp
and scene score plus source/config/runtime provenance. It stores no source
path, frame, audio, name or identity.

A second JSON-only stage applies score floor 0.4 and descending-score temporal
non-maximum suppression. Initial 4-second separation was visually audited and
rejected as too dense; the retained POC default is 10 seconds. Raw peaks remain
immutable, so this threshold can be retuned without decoding again.

Hardware: fanless M4 MacBook Air with 16 GB unified memory, macOS 26.5.2.
No model, network or hardware VP9 decoder was used.

## Results

- Bellpuig: two raw peaks at 0.5 and 3.0 seconds, both below the retained 0.4
  floor, producing zero candidates. The pipeline fails closed rather than
  forcing an event.
- Old Ghost Road: 24 raw peaks over 15–222 seconds. Score floor plus 10-second
  NMS retains nine candidates at 43, 53, 84.5, 95.5, 109.5, 121.5, 163.5,
  193.5 and 222 seconds.
- Skiing: the 5120x2560, 616.392-second, 1.61 GB VP9 source did not complete in
  the bounded execution session and produced no artifact. The installed FFmpeg
  exposes only its software VP9 decoder. Repeating full decode is rejected;
  use a reusable low-resolution proxy or bounded eligible window first.

External artifacts:

- `outputs/scene-events/bellpuig-full-ffmpeg-v1.json`, SHA-256
  `29e4553f9de4ff7d443b9ae27b4577fd67e5a95b37fc56b704b7cf7dda97ec63`.
- `outputs/scene-events/old-ghost-road-full-ffmpeg-v1.json`, SHA-256
  `a63baf46d413f4f475cb11c6962ddacee1914d3bb14159381e9e5784e36722e3`.
- `outputs/scene-change-candidates/old-ghost-road-v2-separation10.json`.
- `outputs/scene-change-candidates/bellpuig-v2-separation10.json`.

## Visual audit and conclusion

A temporary ERP contact sheet of the 14 candidates from the rejected 4-second
policy showed genuine state boundaries: forest, alpine terrain, hut arrival,
indoors, outdoor people and later forest trail. It also showed duplicate scene
states around 79/84.5, 95.5/100, 121.5/126.5 and 193.5/199.5. The sheet was
deleted after review.

The signal passes only as a sparse boundary proposal. It is not motion climax,
subject relevance or scene importance. Merge the nine Old Ghost Road points
into a multi-signal timeline with neutral cardinal candidates next; do not
infer editorial roles from scene score.

## Full-context correction on 2026-08-23

Owner review accepted the four-direction framing coverage but correctly found
the four-second silent packets insufficient for story, chapter or tension
labels. Agent review therefore compared the source over 30-second context,
one-second local sequences and a whole-video five-second timeline.

The source contains distinct cuts at about 53.0/58.8, 78.9/84.6,
95.6/99.8/105.0 and 163.5/168.4 seconds. The former 10-second suppression can
remove one real cut merely because another cut is nearby. The 168.4-second
forest-to-waterfall transition also scores only 0.272 at 10 fps/320 pixels,
so the former 0.4 floor drops a story-relevant boundary. Event 0002 at 84.5
seconds is an exterior-to-interior chapter boundary; 53.0 and 163.5 are
within-chapter rhythm/action cuts.

The accepted candidate default is therefore floor 0.25 with only one-second
local-peak suppression. It preserves cheap-signal recall and leaves chapter,
rhythm and action classification to bounded semantic review. The 0.4/10-second
artifacts above remain reproducible rejected evidence, not the active policy.

The original 2 fps raw artifact also omitted the visible forest-to-waterfall
cut. A bounded 10 fps/320-pixel replay detects it at 168.4 seconds with score
0.272. The active raw-analysis default is therefore 10 fps pending the full
source replay below; this changes proxy comparison cadence, not the bounded
streaming or frame-retention contract.
