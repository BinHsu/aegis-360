# Apple Core ML semantic detector smoke — 2026-07-29

Status: Natural-image person seed observed; bicycle and recall gates not passed

## Question

Does the indexed YOLOv3 Tiny FP16 model produce plausible person or bicycle
seeds on the existing fixed Old Ghost Road sample timestamps?

## Fixed protocol

- Timestamps: 15, 60, 105, 150 and 210 seconds, chosen previously for the
  Apple Vision batch gate
- Four horizon viewports per timestamp: yaw 0, 90, 180 and -90 degrees
- Projection: rectilinear, pitch 0, 100-degree HFOV, 416x416
- Model/checksum: `apple_yolov3_tiny_fp16_v2`,
  `73406178d0f5793d0d5d1e38274acd146a744c2245c9b63a11998a5015925dda`
- Source: `old_ghost_road_360`
- External artifacts:
  `outputs/semantic-detector/old-ghost-road-t{15,60,105,150,210}-v1/`

The versioned runner is
`scripts/run_semantic_detector_multiview_smoke.sh`. It verifies the model
manifest before inference, refuses overwrite, deletes temporary frames, and
persists only labels, confidence, normalized boxes and a privacy-safe summary.

## Results

| Timestamp | Person | Bicycle | Other |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 0 | 0 |
| 60 | 0 | 0 | 0 |
| 105 | 3 | 0 | 0 |
| 150 | 1 | 0 | 0 |
| 210 | 0 | 0 | 0 |

Agent visual inspection of regenerated contact sheets found three visible
people at 105 seconds matching the three high-confidence boxes. At 150 seconds
the -90-degree view contains several riders and bicycles; its one person box
is plausible, but other people and all bicycles are missed. Contact sheets
were temporary and are not persisted or committed.

## Conclusion

The model is sufficient to seed a bounded person-tracking experiment, not to
claim general semantic recall or bicycle detection. Detection appears at only
two of five fixed timestamps, and bicycle count is zero despite visibly
present bicycles at 150 seconds. Do not lower confidence after observing these
results and call that the same gate.

Next use the reviewed 150-second, -90-degree person box to initialize a short
forward tracker sequence. Keep the class as perception provenance; tracking
must not reinterpret it as bicycle identity or story importance.
