# Rendered flat-video shake probe

Status: Protocol implemented; paired real-media v4 110-degree result recorded

## Question

Can fixed-forward and auto-directed flat renders of the same interval be
compared with a cheap, repeatable screen-space motion proxy, including whether
the end of a clip is less stable than its beginning?

## Method

`scripts/probe_render_shake.py` asks the installed FFmpeg to stream a 160x90
grayscale proxy at 6 fps. It performs exhaustive integer block matching
between adjacent frames within an eight-pixel radius. It reports:

- median and p95 translation magnitude;
- median and p95 change in the translation vector (a high-frequency jitter
  proxy that does not penalize a perfectly steady pan as strongly);
- the same values for equal-sized first and last 20% windows;
- last/first median vector-change ratio; and
- SAD improvement over the zero-motion match as a weak match-quality clue.

The implementation stores only two decoded frames. It uses Python's standard
library and installed FFmpeg, downloads nothing, and does not extract images.

Example (run only on local renders with matching interval and FOV):

```sh
python3 scripts/probe_render_shake.py \
  fixed=/path/to/fixed-forward.mp4 \
  auto=/path/to/auto-directed.mp4 > /path/to/shake-report.json
```

Lower vector-change values indicate smoother global screen motion. Compare the
normalized width-fraction fields if proxy dimensions differ. A useful result
requires several frame pairs in both edge windows.

## Acceptance criteria

- A known synthetic integer translation is recovered.
- Identical frames produce zero motion.
- First and last windows contain equal proportions and expose deliberately
  increased alternating motion.
- A real-media conclusion is recorded only after the same source interval,
  projection, FOV, output dimensions, and sampling configuration are used for
  fixed and auto renders.

## Limitations

This is not optical stabilization quality or viewer-comfort ground truth.
Moving subjects, parallax, cuts, exposure changes, rolling shutter, and
textureless scenes can affect it. It estimates translation only, not roll or
perspective rotation. Motions outside the search radius may clip or mismatch.
Use it for paired triage and localization, then inspect the corresponding
video. The first/last comparison is descriptive and is not a causal claim.

## Result

The synthetic unit tests pass.

A paired probe was run on the v4 110-degree fixed-forward and auto-directed
Old Ghost Road renders at 6 fps with a 160x90 proxy. The measured pixel-space
translation magnitudes were:

| Window/metric | Fixed-forward | Auto-directed |
|---|---:|---:|
| First-window p95 step | 1.75 px | 2.81066 px |
| Last-window median step | 2.0 px | 2.11803 px |
| Last-window p95 step | 10.25305 px | 10.32843 px |
| Last-window p95 vector change | 5.78208 px | 6.60351 px |

Both renders have a large last-window p95 step of about 10.3 pixels, and the
auto-directed render does not improve the reported tail metrics. Together
with the owner's review that 110- and 120-degree renders had no significant
comfort difference, this supports the bounded diagnosis that global/source
motion dominates the uncomfortable ending and that FOV is not the primary
remedy.

This conclusion remains triage evidence, not a causal stabilization claim.
The probe fits translation only. It cannot separate camera rotation, roll,
perspective deformation, moving-subject motion, or parallax, and its
translation estimate can itself be biased by parallax. The result therefore
does not establish optical stabilization quality or viewer comfort and does
not show that auto directing caused the source motion.
