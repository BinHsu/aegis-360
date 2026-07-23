# System overview

Status: Active design

## Goal

The POC turns a monoscopic equirectangular recording into a chronological
1920x1080 rectilinear **Full Story** without asking the user to select a
subject. It must show whether an explainable global auto-director beats simple
fixed-forward and greedy baselines on the three public benchmarks.

The only required environment is the developer's M4 MacBook Air with 16 GB
unified memory. Time-to-evidence takes precedence over portability. Apple-only
tools are acceptable when they shorten the experiment; Core ML and Metal are
not required until measurements justify them.

## Data flow

```text
source + validated projection
  -> reusable low-resolution proxy
  -> perception observations and tracks
  -> interest evidence and candidate shots
  -> baseline/global plans
  -> decision traces and proxy previews
  -> one source-resolution render of the selected plan
```

Analysis artifacts are reusable so planner changes do not rerun perception or
full-resolution rendering. Media, models, caches, and outputs live below the
configurable external data root; the repository contains manifests, code,
small synthetic fixtures, and summaries only.

## Component boundaries

- Input validation identifies streams, timing, projection evidence, color and
  audio properties; ambiguous projection requires an explicit override.
- Geometry owns coordinate conventions, seam handling, projection and camera
  interpolation.
- Perception emits observations and persistent identities, not editorial
  decisions.
- Interest modeling emits named, normalized evidence for candidate views.
- Planning selects a time-consistent shot path and explains utility/cost.
- Rendering follows the selected path without silently changing it.
- Decision traces connect every output choice to inputs, configuration and
  evidence without embedding personal data or absolute paths.

## POC boundaries

Native `.360`/`.insv`, de-stitching, GUI, accounts, cloud services,
personalization and aggressive highlight deletion are excluded. Full Story
retains chronology and most content; event scores are retained for later
Highlights work.

## Unverified hypotheses

- A proxy between 960x480 and 1280x640 at a reduced sampling rate will preserve
  enough evidence for useful directing.
- A global DP/DAG plan will be preferred to greedy hysteresis by viewers.
- FFmpeg is sufficient for correctness and initial preview/render iteration.

The experiments index defines how these claims are tested; none is an observed
result yet.
