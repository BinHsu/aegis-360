# Scene-story context and closed labels v1

Status: Executed on 2026-08-23

## Question

Can sparse scene events expose enough original-video context to distinguish a
chapter boundary from an action/rhythm cut without making a model watch every
second? A pass establishes a bounded evidence contract. It does not select a
model, camera view or edit.

## Source-context finding

The owner accepted the earlier four-cardinal framing coverage but found its
four silent seconds insufficient for story, chapter or tension judgments. The
agent therefore reviewed Old Ghost Road with 30-second four-cardinal context,
one-second cut sequences and a five-second whole-film timeline.

- 53.0 seconds is a hard cut within the ridge/travel chapter.
- 84.6 seconds is a hard exterior-to-interior chapter boundary.
- 163.5 seconds is a hard cut continuing forest riding.
- 168.4 seconds is a hard forest-to-waterfall activity/chapter transition.
- 222.0 seconds is a gradual ending transition.

These are agent source-context labels. They are not owner ground truth. The
owner statement establishes view coverage only.

## Packet and transient-media contract

`aegis360.scene-story-review-packet.v1` binds an exact Timeline v2 and context
grid. Around the first/last scene signal it schedules far, near and 0.25-second
boundary anchors, normally six timestamps spanning about 30 seconds. Boundary
clipping and timestamp deduplication keep two to six samples.

Each timestamp is one temporary 2x2 contact sheet containing the four declared
cardinal candidates in grid order. Thus an adapter receives at most six images
while the renderer processes at most 24 bounded 384x216 source viewports. The
packet also includes event position, event count and previous/next event
summaries. It contains no pixels, audio, identity or editorial answer.

A real event 0008 run rendered six 768x432 PNGs. The diagnostic adapter probed
all six against the transient index, and the runner's postcondition verified
temporary-directory deletion. The first CLI attempt placed width/height after
the positional packet; `argparse.REMAINDER` treated them as the adapter command
and failed after cleanup. Options must precede positional inputs.

## Closed semantic evidence

`aegis360.scene-story-semantics.v1` separates four axes:

- structural role: chapter boundary, within-chapter cut or ending transition;
- narrative function: context, action continuation, activity transition,
  tension build/release or closing;
- change type: hard cut, gradual transition or motion peak;
- ordinary-viewer value: primary, supporting or low.

Observed evidence must complete all axes. Abstention must make every axis
unknown. Human/agent provenance cannot claim a model asset; local-model
provenance requires an exact checksum. The output has no confidence, free text,
geometry or edit command.

Five committed configs under `benchmarks/scene-story-labels/` bind to external
packets and produce these semantic SHA-256 values:

- 0005: `5fa143b6f1acc6f99a38169f10b37a792019bc7b14d1cdc8b51de45c3eeceb0a`;
- 0008: `4047943c16b3806e1b8da77bb5f818a091d768e1b769459a40bc97b69d83bbbf`;
- 0018: `107f6a80b3f9083c5e048368dea7cb39338c2c1e3255914f02da156e6445e11f`;
- 0019: `57c3f29a81e24bf3a26cf754f3564e45587392cb2eedf1a9b77155c7a92af261`;
- 0024: `37acbaa46fda198411f814a2502d28eeee39a5c9c96f1686b2c2d0f2def13911`.

## Conclusion and next gate

Local context plus whole-video position is sufficient to encode representative
story roles without per-second VLM sampling. The global planner must consume
the complete ordered label sequence and retain final authority. Story labels
must constrain cut/dwell/transition policy separately from candidate-view
relevance; they do not identify the best direction by themselves.
