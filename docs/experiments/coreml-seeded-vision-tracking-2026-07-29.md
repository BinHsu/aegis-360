# Core ML-seeded Vision tracking — 2026-07-29

Status: Isolated short track accepted; crowded identity continuity rejected

## Question

Can a visually reviewed Core ML `person` detection seed the existing
`VNTrackObjectRequest` probe without immediately losing the target?

## Geometry contract

The detector smoke used 416x416 views while the original tracker runner used
640x360. Repeating detection at 640x360 returned no seed, so coordinates were
not transferred between projections. `run_vision_tracking_gate.sh` now accepts
optional `WIDTH HEIGHT`, preserving 640x360 defaults; both experiments below
use the detector's exact 416x416, yaw=-90, pitch=0, 100-degree HFOV geometry.

## Runs

Both runs cover three seconds at 4 fps and contain 12 requested observations.

| Start | Scenario | Tracked/lost/error | Max center step | Visual result |
| ---: | --- | --- | ---: | --- |
| 105 s | isolated standing person | 12/0/0 | 0.400° | same visible person retained |
| 150 s | overlapping riders/bikes | 12/0/0 | 3.556° | box persists but person identity is ambiguous and may transfer |

External evidence:

- `outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v1/`
- `outputs/vision-tracking-gate/old-ghost-road-t150-yawm90-person-v1/`

These v1 artifacts retain valid boxes but their spherical pitch/step metrics
used a legacy 16:9 assumption. Use the corresponding `-v2/` artifacts for
correct 416x416 spherical metrics. See
`native-detector-refresh-trace-2026-07-29.md`.

Temporary box-overlay contact sheets were inspected by the agent and deleted
from the durable evidence boundary. The privacy-safe numeric traces remain.

## Conclusion

`tracked_frames == requested_frames` is box continuity, not identity proof.
The isolated 105-second sequence passes a bounded short-track visual gate.
The crowded 150-second sequence does not establish identity continuity despite
12/12 API observations. Vision tracking may be used between detector refreshes,
but crowded-scene reassociation must fail closed or remain explicitly
ambiguous. Never relabel either person track as bicycle or main character.

Next implement a class-aware detector-refresh association policy with an
explicit ambiguous outcome. Geometry can confirm compatibility but cannot
create semantic identity.
