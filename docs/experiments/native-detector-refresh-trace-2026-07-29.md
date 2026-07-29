# Native detector-refresh trace — 2026-07-29

Status: Isolated-person trace observed; detector miss correctly fails closed

## Question

Can native Core ML detector refreshes be compared with Apple Vision tracking
without silently reassigning identity or granting editorial persistence?

## Geometry correction

The first 416x416 tracking artifacts used a legacy 16:9 vertical-FOV
assumption when converting boxes to spherical pitch. Boxes and the visual
tracking audit remain valid, but v1 spherical pitch/step values are superseded.
The native input and provenance now carry viewport width/height and compute
vertical FOV from the actual aspect ratio.

Replacement artifacts:

- `outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v2/`
- `outputs/vision-tracking-gate/old-ghost-road-t150-yawm90-person-v2/`

Both preserve 12/12 box observations. At 105 seconds the first pitch changes
from -0.1044 rad in v1 to -0.1841 rad in v2; yaw is unchanged. At 150 seconds
it changes from 0.2991 to 0.5014 rad. Do not use v1 spherical metrics.

## Refresh run

The visually accepted isolated 105-second person track was refreshed at 106
and 107 seconds with the same 416x416, yaw=-90, pitch=0, 100-degree viewport.
`scripts/build_native_refresh_trace.py` combines exact-timestamp tracker rows
and detector JSON through the backend-independent refresh policy.

Observed trace:

| Time | Detector | Outcome | Persistence |
| ---: | --- | --- | --- |
| 106 s | one nearby `person` | compatible, identity unverified | denied |
| 107 s | no `person`; railing box labeled `chair` | missing | denied |

Agent overlay inspection confirms that the tracker remained on the same
standing person at both timestamps. At 106 seconds the detector person box
overlaps that target. At 107 seconds the detector misses the person and places
a chair box on the railing. The fail-closed adapter correctly does not use the
wrong-class box to reset the person track.

The privacy-safe trace is
`outputs/vision-tracking-gate/old-ghost-road-t105-yawm90-person-v2/`
`refresh-trace.json`. It contains no pixels, paths or embeddings.

## Conclusion

A refresh miss does not prove tracking loss. It must enter a bounded missing
grace period; a wrong-class detection must never reset the tracker. A single
compatible refresh can maintain operational continuity but still cannot
establish identity or editorial persistence. Next connect refresh outcomes to
the existing lifecycle policy and test missing-grace recovery.
