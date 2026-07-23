# aegis-360 — Project Scaffold Spec (v2)

This document specifies the initial file structure for the **aegis-360**
project. Each section below corresponds to one file to create in the repo.
Create each file with the exact content shown under its heading.

**Layering principle (why the split):**
- `AGENTS.md` = harness only — how an agent operates in this repo (scope,
  stack, commands, conventions). Short, stable, tool-facing.
- `docs/adr/` = Architecture Decision Records — *settled* decisions with
  rationale and trade-offs.
- `docs/design/` = exploration / open problems not yet decided.
- `README.md` = human-facing — what this is, why it matters, the demo.
  Agents don't need the pitch; hiring readers do.

`CLAUDE.md` is a one-line bridge that imports `AGENTS.md`, so Claude Code
and Codex both read the same single source of truth.

Target directory tree:

```
.
├── AGENTS.md
├── CLAUDE.md
├── README.md
└── docs/
    ├── adr/
    │   ├── 0001-start-from-equirectangular.md
    │   ├── 0002-two-phase-detector-stack.md
    │   ├── 0003-input-scope-no-destitch.md
    │   └── 0004-mac-only-v1.md
    └── design/
        └── hard-parts.md
```

---

## FILE: `AGENTS.md`

```markdown
# aegis-360

## Scope
Input: already-stitched equirectangular MP4 (2:1 aspect ratio), H.264/H.265.
Out of scope: proprietary .insv / .360 de-stitching.
POC goal: single subject → detect + track → reproject to a flat
rectilinear video → smooth the camera path → cut dead-air segments →
output one flat MP4 plus a before/after comparison clip.

Hard constraints (these define the product, not just preferences):
- Fully offline. No network calls, no account, no login, no telemetry.
- macOS only for v1 (see ADR 0004).

## Stack
Phase 1 (POC — prove the pipeline):
- Python + FFmpeg (frame extraction, v360 reprojection, encode)
- Ultralytics YOLO (v8/v11) on MPS — person detection
- ByteTrack / BoT-SORT (built into Ultralytics) — cross-frame subject lock

Phase 2 (v1 — squeeze Apple Silicon, only after POC works):
- Core ML + Neural Engine for detection
- VideoToolbox for hardware 8K decode/encode
- Metal / MPS for equirectangular→rectilinear reprojection
See ADR 0002 for why this is staged rather than done upfront.

## Conventions
<!-- Fill in as the code lands: -->
- Build / setup: TBD
- Run: TBD
- Test: TBD
- Lint / format: TBD
- Directory layout: TBD

## Decisions
See docs/adr/ for the rationale behind stack, scope, and platform choices.
Open problems and unsettled exploration live in docs/design/.
```

---

## FILE: `CLAUDE.md`

```markdown
@AGENTS.md
```

*(That single line is the whole file. It expands AGENTS.md into Claude
Code's context at launch. Add Claude-specific overrides below it only if
a real need appears — otherwise leave it as one line.)*

---

## FILE: `README.md`

```markdown
# aegis-360

Turn raw 360 video into a watchable flat video — automatically, and fully
offline. aegis-360 tracks the main subject and cuts the dead air,
producing a normal rectilinear clip from spherical footage with no manual
keyframing, no account, and no internet connection.

## Why

360 cameras capture everything, which pushes the editing burden to
*after* the shot: you have to decide where to look and what to keep.

The best automatic tool for this — Insta360's Deep Track, in Insta360
Studio — is genuinely good, and it will even track footage from other
cameras once you convert it to equirectangular. But Insta360 Studio
requires an Insta360 account login and is software from a Chinese vendor.
For a real set of users — government, defense, and security-sensitive
environments (Insta360 Studio is formally restricted in the US Dept. of
Veterans Affairs technology reference model, for example) — installing it
is simply not allowed. These users often shoot on GoPro (US-made)
hardware and have excellent 8K 360 footage, but no offline, self-hosted
way to auto-edit it: GoPro's own AI tracking is mobile-only, and its
desktop story is manual reframing plugins.

aegis-360 fills exactly that gap: an offline, open-format, desktop tool
that does automatic subject tracking **and** dead-air removal — the
combination no one else ships — without touching any closed ecosystem.

## What it does (POC)

- Detects and tracks a single subject across a 360 clip
- Reprojects a virtual camera to follow them, as a normal flat video
- Smooths the camera path so the motion isn't jittery
- Cuts static / low-activity segments (dead air)
- Outputs a flat MP4 and a before/after comparison clip

## Design principles

- **Offline by construction** — no network, no account, no telemetry.
- **Open formats only** — standard equirectangular in, standard MP4 out.
- **Mac-native** — v1 targets Apple Silicon and squeezes it (Neural
  Engine, VideoToolbox, Metal) rather than aiming for a generic build.

## Status

Proof of concept. See `docs/adr/` for design decisions and
`docs/design/` for open problems.

## Demo

<!-- Drop the before/after clip / GIF here — this is the most important
part of the repo for a first-time viewer. -->
```

---

## FILE: `docs/adr/0001-start-from-equirectangular.md`

```markdown
# 1. Start the pipeline from equirectangular input

Status: Accepted

## Context

360 cameras record in proprietary formats (Insta360 dual-fisheye .insv,
GoPro EAC .360), each with its own lens model and stabilization data.
But essentially all of them can export a stitched equirectangular MP4
(2:1), and equirectangular is the universal interchange format for 360
video.

## Decision

The pipeline assumes its input is an already-stitched equirectangular
MP4. Stitching / de-stitching from proprietary raw files is not part of
the pipeline.

## Consequences

- The tool only has to understand one input format, sidestepping every
  vendor's proprietary container.
- Camera-app stabilization and horizon-leveling are already applied to
  this input, so the tool does not need IMU/GPS telemetry (which is also
  stripped from such exports anyway). Subject tracking is purely visual.
- Users must run their camera app's export step first. Accepted for the
  offline/open-format scope; a future version could add de-stitching
  (see design notes).
```

---

## FILE: `docs/adr/0002-two-phase-detector-stack.md`

```markdown
# 2. Two-phase stack: generic POC first, Apple-native v1 second

Status: Accepted

## Context

The pipeline needs person detection + cross-frame tracking, plus heavy
video decode/reproject/encode. On Apple Silicon there is a lot of
platform-specific performance to exploit (Neural Engine via Core ML,
VideoToolbox hardware codecs, Metal/MPS, unified memory). But adopting
all of that upfront means debugging Core ML conversion and Metal shaders
before the core function even works.

Detector candidates considered:
- Ultralytics YOLO (v8/v11) — AGPL-3.0 (fine, not commercial), built-in
  ByteTrack/BoT-SORT, runs on MPS, largest ecosystem, existing 360
  tracking repos build on it.
- RF-DETR (Roboflow, US) — Apache 2.0, higher accuracy, better on
  occlusion; newer ecosystem.
- Academia Sinica YOLOv7/v9 (Taiwan) — strong detection, less packaged
  tooling.

Goal is a portfolio POC, so AGPL is not a blocker.

## Decision

Stage the work:
- **Phase 1 (POC):** Python + FFmpeg + Ultralytics YOLO on MPS. Prove
  detect → track → reproject → smooth → cut → export end-to-end.
- **Phase 2 (v1):** replace hotspots with Apple-native acceleration —
  Core ML + Neural Engine for detection, VideoToolbox for 8K
  decode/encode, Metal/MPS for reprojection.

Do not start Phase 2 until Phase 1 produces a watchable output.

## Consequences

- Fastest path to a working demo; most reference material available.
- Phase 2 is where the "squeeze Apple Silicon" story (and the thermal
  headroom on a fanless Air) gets demonstrated — a concrete
  performance-engineering narrative for a portfolio.
- If a cleaner license ever matters, RF-DETR (Apache 2.0) or Academia
  Sinica YOLO are the fallbacks; this ADR would be superseded.
- YOLO accuracy degrades on distorted equirectangular frames; mitigation
  is a design problem, tracked in the hard-parts note.
```

---

## FILE: `docs/adr/0003-input-scope-no-destitch.md`

```markdown
# 3. Exclude de-stitching from scope

Status: Accepted

## Context

Handling proprietary raw files (.insv, .360) means reimplementing each
vendor's lens model and stabilization — the most closed, most
labor-intensive part of the 360 stack, and the thing camera apps already
do well.

## Decision

aegis-360 does not de-stitch. It starts from stitched equirectangular
MP4 only (reinforces ADR 0001).

## Consequences

- Keeps the project focused on its actual differentiators: subject
  tracking + dead-air removal, not stitching.
- Test footage can come from public equirectangular clips without owning
  any specific camera.
- A tool aimed at "GoPro footage end-to-end" would eventually need .360
  handling (via existing FFmpeg forks / max2sphere). Deliberately
  deferred as future work.
```

---

## FILE: `docs/adr/0004-mac-only-v1.md`

```markdown
# 4. Ship v1 as macOS-only

Status: Accepted

## Context

Cross-platform support multiplies effort (FFmpeg build differences, GPU
backend differences, packaging) and forces generic code paths that can't
exploit any one platform deeply. The developer's machine is Apple Silicon
(M4 Air), and the target audience (security-sensitive / institutional /
self-reliant users) skews heavily toward Mac.

## Decision

v1 targets macOS on Apple Silicon only, and deliberately exploits
platform-specific acceleration (see ADR 0002 Phase 2) rather than staying
portable.

## Consequences

- Frees effort to go deep: Neural Engine, VideoToolbox, Metal, unified
  memory — none of which a portable build could fully use.
- Hardware codecs (VideoToolbox) also mitigate thermal throttling on the
  fanless Air when processing long 8K clips.
- Excludes Windows/Linux users for now. Acceptable: the goal is a deep,
  convincing portfolio artifact, not market coverage. Portability is a
  possible future direction, not a v1 requirement.
```

---

## FILE: `docs/design/hard-parts.md`

```markdown
# Hard parts / open problems

Unsettled exploration — NOT decisions. Promote an item to an ADR only
once it's actually decided with a rationale.

## Coordinate transform (highest risk)
Mapping a 2D detection box on the equirectangular frame → spherical
lat/lon → a virtual-camera yaw/pitch for reprojection. This is the
heaviest math in the project and where correctness bugs will hide.
FFmpeg's `v360` filter (Phase 1) / Metal (Phase 2) handles the final
reprojection; the open question is the bbox→angle conversion feeding it.

## Detection accuracy on distorted frames
YOLO is trained on normal images; equirectangular badly warps subjects
near the poles. Options to explore: slice the sphere into several
perspective views, detect in each, map results back — at the cost of
more compute. Undecided.

## Camera-path smoothing
Per-frame subject coordinates jitter; following them raw is nauseating.
Need temporal smoothing (moving average or Kalman + damping) on the
virtual camera's yaw/pitch. This is the single biggest driver of whether
the output *feels* smooth. Easy to get wrong.

## Dead-air detection heuristic
What counts as "dead air"? Candidate signals: low subject motion, low
overall optical flow, no scene change over a window. Needs tuning against
real footage — too aggressive cuts real moments, too soft leaves boredom.
This is a core differentiator, so worth getting right.

## Subject handoff (deferred)
Choosing whom to follow and when to switch in multi-person scenes is
product logic, not detection. Out of scope for the single-subject POC;
noted so it isn't forgotten.

## Apple Silicon acceleration trade-offs (Phase 2)
Core ML conversion of the detector may lose a little accuracy
(quantization) and needs re-validation. VideoToolbox codec support and
the Metal reprojection path need to be verified against 8K equirectangular
specifically. Unified memory should reduce copies but the win needs
measuring, not assuming. Don't enter this until Phase 1 works.

## 8K compute
Real GoPro Max2 footage is True 8K. Detection + reprojection at that
resolution is heavy; a fanless Air will thermal-throttle without hardware
codecs. Phase 1 can downscale / sample frames; Phase 2's VideoToolbox
path is the real answer.
```

---

## After creating the files

1. `AGENTS.md` is the single source of truth. Both Claude Code (via the
   `@AGENTS.md` import in `CLAUDE.md`) and Codex (natively) read it.
2. Keep `CLAUDE.md` at one line unless a genuinely Claude-specific
   instruction is needed.
3. As code lands, fill in the `## Conventions` block in `AGENTS.md` with
   real build/run/test commands — that's the part agents most need.
4. When a design item in `hard-parts.md` gets settled, write a new ADR
   for it rather than editing the note in place. Decisions accrete;
   history stays readable.
5. Put the pitch and the demo clip in `README.md`, not in the agent
   files — the agent needs to know how to build, the human needs to know
   why it matters.

## First task suggestion (lowest-risk place to start)

Build the input front-end: download a public equirectangular clip
(yt-dlp), verify it's 2:1 equirectangular with the right metadata
(ffprobe), and extract frames. It's self-contained, has no dependency on
the hard parts, and gives you a verified test asset to build the rest of
the pipeline against.
```
