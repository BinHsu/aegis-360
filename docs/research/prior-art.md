# Prior art and research directions

Verified: 2026-07-23

## Established prior art

Automatic 360-to-normal-view reframing is not new. Su, Jayaraman, and Grauman's
*Making 360° Video Watchable in 2D* (2017) generates candidate normal-FOV views,
scores them, and selects a coherent viewing trajectory. [Paper](https://arxiv.org/abs/1703.00495)

This establishes several non-exclusive ideas relevant to the POC:

- represent possible normal-field-of-view shots on the sphere;
- score candidate views for likely human interest;
- optimize a sequence rather than selecting each frame independently; and
- evaluate watchability and viewer preference, not detector accuracy alone.

FFmpeg's [`v360` filter](https://ffmpeg.org/ffmpeg-filters.html#v360) is prior
infrastructure for projection conversion. It does not decide where the virtual
camera should look.

## Research areas to draw from

- 360 saliency and viewport prediction
- spherical detection and seam-aware tracking
- video highlight and event detection
- active-speaker and interaction-region selection
- computational cinematography and virtual-camera planning
- temporal dynamic programming, Viterbi paths, and candidate-shot DAGs
- camera-motion comfort constraints: velocity, acceleration, jerk, dwell, and
  reversal penalties

These are categories to investigate, not accepted implementation choices.

## Clean implementation boundary

The project should implement from public papers, standard mathematical methods,
and its own requirements/tests. Vendor patents and marketing descriptions may
identify risks or terminology but are not implementation specifications.

For a future commercial release, code/model/data licenses and patent freedom to
operate require separate professional review. This document is technical
research, not a legal opinion.

## Baselines and falsification

The main planner should be compared with:

1. fixed-forward view;
2. greedy motion/saliency selection with hysteresis; and
3. a global candidate-shot planner.

The product hypothesis is weakened if the global method does not improve blind
pairwise viewer preference or event coverage enough to justify its complexity.
