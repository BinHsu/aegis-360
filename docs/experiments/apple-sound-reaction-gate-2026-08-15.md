# Apple SoundAnalysis reaction-event gate — 2026-08-15

Status: Bounded reaction candidates accepted; no camera-cut authority

## Question

Can an OS-provided, offline classifier expose applause timing in the licensed
Gaudeamus benchmark without treating volume or a sound label as editorial
ground truth?

## Contract

`scripts/run_apple_sound_events.py` extracts at most 300 seconds of temporary
mono 44.1 kHz PCM, compiles the native gate, runs Apple's built-in
`SNClassifierIdentifierVersion1`, validates a closed artifact, and deletes the
PCM. Durable output contains no source path, audio or transcript. Only `music`,
`applause`, `clapping` and `cheering` are retained. Confidence is model evidence,
not utility, sound direction or source identity.

`scripts/build_reaction_intervals.py` requires applause and clapping to each
reach 0.5 in at least two overlapping classifier windows. These correlated
labels come from one model, so the threshold remains a POC hypothesis. An
interval is only a candidate for later visual/role validation and cannot
authorize a camera cut.

## Real result

The 128-second Gaudeamus audio run completed in 6.2 seconds including PCM
extraction and Swift compilation. SoundAnalysis emitted 84 three-second windows
at 50% overlap. The bounded aggregation produced:

- 9.0–15.0 seconds: 3 supporting windows; peak applause 0.848849 and clapping
  0.803971.
- 109.5–124.5 seconds: 9 supporting windows; peak applause 0.776286 and
  clapping 0.894515.

Four-view visual inspection places the intervals at the performance opening
and ending, but low source resolution does not establish visible per-person
clapping. A separate 127-second six-view detector run completed in 23.601
seconds with 579 person boxes. Person evidence persists through most of
109.5–118.5, nearly disappears by 118.5–124.5 and is absent at 124.5–127,
matching the title-card transition. The detector finds no people in the distant
audience viewport, so it may bound live-scene availability but cannot validate
an audience reaction shot.

## Decision

Retain the two path-free reaction candidates. Next generate deterministic
context-view geometry, bind human/model roles only to declared candidates, and
intersect reaction timing with live-scene availability. Do not add these scores
to the current greedy weights or render a reaction edit yet.

External evidence:

- `outputs/sound-events/gaudeamus-full-apple-v1/events.json`
- `outputs/reaction-intervals/gaudeamus-full-apple-v1-threshold-p5/intervals.json`
- `outputs/semantic-events/gaudeamus-full-six-view-yolox-v2/`
