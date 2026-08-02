# YOLOX multi-view semantic-event gate

Status: Bounded acquisition gate passed; identity/lifecycle integration pending

## Question and decision unlocked

Can one load-once Core ML detector continuously sample enough of a 360-degree
scene on the reference Mac to expose privacy-safe person/bicycle evidence,
without persisting pixels or paths? A pass permits work on spherical duplicate
merging and lifecycle acquisition. It does not permit a directing-quality,
identity, or real-time claim.

## Frozen contract

- Source: `old_ghost_road_360`, SHA-256
  `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`.
- Interval: 60.0 through 90.0 seconds; 30 seconds total.
- Projection: six 416x416 rectilinear views from
  `config/semantic-multiview-six-v1.json`; front/right/back/left at pitch zero,
  plus pitch +60/-60 degree views; 100-degree horizontal FOV.
- Cadence: 4 fps per view, 120 frames per view and 720 event rows total.
- Detector: validated FLOAT32 YOLOX-Tiny Core ML package derived from official
  `0.1.1rc0` weights, confidence 0.25 and NMS IoU 0.45.
- Only accepted person and bicycle detections enter the artifact. Scores remain
  perception evidence only. Boxes are normalized in-frame top-left geometry.
- One model load and six serial FFmpeg raw-BGR streams. No frames, audio,
  embeddings, source paths, or identities are persisted.
- Output directories are atomic and refuse overwrite.

The schema is `aegis360.semantic-detector-events.v1`. Synthetic tests fixed
ordering, geometry bounds, path-free identifiers, viewport references,
privacy declarations, and person/bicycle-only behavior before this media run.

## Environment and procedure

- Hardware: fanless Apple Silicon MacBook Air M4, 16 GB unified memory.
- OS: macOS 26.5.2 (25F84), arm64.
- FFmpeg: 8.1.1 with Apple clang 21.0.0.
- Core ML Tools environment: Python 3.12, Core ML Tools 9.0 and Torch 2.7.0
  conversion environment already recorded by the equivalence protocol.
- Thermal state was not instrumented. Host swap counters were unavailable in
  the restricted run, so this result is not a sustained thermal or swap claim.

Run from the repository root after setting `AEGIS_DATA_DIR`:

```sh
"$AEGIS_DATA_DIR/venvs/yolox-coreml-py312-torch27/bin/python" \
  scripts/run_yolox_multiview_events.py \
  "$AEGIS_DATA_DIR/benchmarks/originals/old_ghost_road_360.webm" \
  "$AEGIS_DATA_DIR/models/yolox/converted/coremltools-9.0-torch-2.7.0-float32-generated-v2/YOLOX-Tiny-0.1.1rc0.mlpackage" \
  config/semantic-multiview-six-v1.json \
  "$AEGIS_DATA_DIR/outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v1" \
  --source-id old_ghost_road_360.webm \
  --start-seconds 60 --duration-seconds 30
```

## Results

- Elapsed wall time: 12.614 seconds, including projection, model load,
  inference, decode/NMS, validation and artifact serialization.
- Model load: 0.289 seconds; Core ML inference: 7.997 seconds; decode/NMS:
  0.520 seconds.
- Peak RSS: 365,527,040 bytes, well below the repository's 10 GB investigation
  threshold for this bounded run.
- All six streams produced exactly 120 frames. The artifact contains 720
  timestamp/viewport rows, 238 accepted person boxes and 17 bicycle boxes;
  25 out-of-frame geometry results were rejected rather than clipped.
- Detection-bearing samples: front 51, right 57, left 22, down 45 and up 19.
  Back produced none. Across all views, at least one detection occurs at 95 of
  120 timestamps, from 60.0 through 89.75 seconds.

Agent inspection of a six-view contact sheet at five-second intervals confirms
that the interval contains several people outside the hut and later indoors.
Right, left and down views expose people that a fixed front view cannot retain.
This is materially broader semantic acquisition than the earlier isolated
bicycle lifecycle. The contact sheet was temporary, contained source pixels,
and was not committed or placed in the durable event artifact.

The 19 `up`-view person boxes are suspect: their mean normalized box area is
about 0.739 and all exceed 0.15. They are likely projection-boundary or overlap
artifacts rather than nineteen trustworthy subject observations. Counts across
views also include unresolved duplicates. Therefore raw box count is not
candidate count and cannot be used as editorial utility.

## Conclusion and next gate

The bounded acquisition gate passes. Six serial views at 4 fps are comfortably
fast and memory-bounded on the reference machine, and they expose sustained
non-ego people across headings. The event layer is deliberately pre-identity:
it neither merges spherical duplicates nor associates observations over time.

Next, convert accepted viewport boxes to spherical observations, merge
same-timestamp duplicates with provenance retained, and feed conservative
fresh-candidate acquisition/lifecycle logic. Fail closed on pole/boundary
artifacts and never reuse a terminated ID. Only after a sustained, visually
credible non-ego lifecycle survives the existing hold/margin may the planner
or renderer be invoked.

External evidence is under
`outputs/semantic-events/old-ghost-road-t60-90-six-view-yolox-v1/` relative to
`AEGIS_DATA_DIR`. It contains only `events.json` and `metrics.json` and must not
be committed.
