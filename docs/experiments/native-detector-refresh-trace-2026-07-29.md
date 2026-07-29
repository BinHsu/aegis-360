# Native detector-refresh trace — 2026-07-29

Status: Isolated-person miss and bounded recovery observed

## Question

Can native Core ML detector refreshes be compared with Apple Vision tracking
without silently reassigning identity or granting editorial persistence?

## Geometry correction

The first 416x416 tracking artifacts used a legacy 16:9 vertical-FOV
assumption when converting boxes to spherical pitch. Boxes and the visual
tracking audit remain valid, but v1 spherical pitch/step values are superseded.
The native input and provenance now carry viewport width/height and compute
vertical FOV from the actual aspect ratio.

Replacement and recovery artifacts:

- `outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v2/`
- `outputs/vision-tracking-gate/old-ghost-road-t150-yawm90-person-v2/`
- `outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v3/`

Both preserve 12/12 box observations. At 105 seconds the first pitch changes
from -0.1044 rad in v1 to -0.1841 rad in v2; yaw is unchanged. At 150 seconds
it changes from 0.2991 to 0.5014 rad. Do not use v1 spherical metrics.

## Refresh run

The visually accepted isolated 105-second person track was refreshed at 106,
107 and 108 seconds with the same 416x416, yaw=-90, pitch=0, 100-degree viewport.
`scripts/build_native_refresh_trace.py` combines exact-timestamp tracker rows
and detector JSON through the backend-independent refresh policy.

Observed trace:

| Time | Detector | Outcome | Persistence |
| ---: | --- | --- | --- |
| 106 s | one nearby `person` | compatible, identity unverified | denied |
| 107 s | no `person`; railing box labeled `chair` | missing | denied |
| 108 s | one nearby `person`; railing box labeled `chair` | compatible, identity unverified | denied |

Agent overlay inspection confirms that the tracker remained on the same
standing person at all three timestamps. At 106 seconds the detector person box
overlaps that target. At 107 seconds the detector misses the person and places
a chair box on the railing. At 108 seconds the person box and tracker box again
overlap the same person, while the railing remains mislabeled `chair`.

The fail-closed adapter filters detections by the requested track class before
converting their geometry. A malformed wrong-class box therefore cannot poison
a valid person refresh, while malformed same-class evidence still fails closed.

The original two-event privacy-safe trace is
`outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v2/`
`refresh-trace.json`. It contains no pixels, paths or embeddings.
The three-event recovery trace was mechanically validated at
`/tmp/old-ghost-road-t105-yawm90-person-v3-refresh-trace.json`; automatic
permission review timed out before it could be copied beside the external v3
artifact, so that temporary file is evidence rather than a durable repo
dependency.

## Conclusion

A refresh miss does not prove tracking loss. The observed
compatible→missing→compatible sequence demonstrates the intended bounded
missing-grace recovery while Vision continuously tracks the same visible
person. A wrong-class detection never resets or invalidates that person track.
Operational continuity still cannot establish identity or editorial
persistence. Next persist and test a privacy-safe lifecycle trace derived from
these refresh outcomes and real tracker confidences.
