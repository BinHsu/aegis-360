# aegis-360

## Mission

Build an offline, camera-agnostic 360 video auto-director. Given a
monoscopic equirectangular video, the system analyzes the whole recording,
chooses what an ordinary viewer is most likely to find interesting, plans a
smooth virtual-camera path, and exports a normal rectilinear video without
requiring the user to select a subject.

The POC delivers **Full Story** first: preserve chronology and most content
while choosing the viewpoint automatically. Highlight selection and
aggressive dead-air removal are the next phase, but analysis outputs should
retain the interest and event scores needed by that phase.

## Scope

- Input: FFmpeg-decodable monoscopic equirectangular video.
- Initially guaranteed inputs: MP4 with H.264/H.265 and WebM with VP8/VP9.
- Input validation must inspect projection/metadata and support an explicit
  override; a 2:1 aspect ratio alone does not prove equirectangular input.
- Output: 1920x1080 H.264 MP4 for the POC, plus a machine-readable decision
  trace and a debug/baseline comparison.
- Out of scope for the POC: proprietary Insta360 `.insv` and native GoPro
  `.360` decoding/conversion, de-stitching, GUI, cloud processing, accounts,
  telemetry, cross-platform support work, and personalized editing
  preferences.

## Reference hardware

The only required POC environment is the developer's fanless Apple Silicon
MacBook Air with an M4, 16 GB unified memory, and external storage for models
and media. Optimize for time-to-evidence and stable execution on this machine.
Cross-platform support is not a POC concern, and Apple ecosystem lock-in is
acceptable when it shortens implementation or benchmark time.

- Use VideoToolbox, MPS, Core ML/Neural Engine, or Metal when a measured
  bottleneck or faster implementation path justifies them; none is a POC goal
  by itself.
- Profile actual compute placement instead of assuming ANE execution.
- Use unified-memory-friendly buffers where practical, but treat 16 GB as a
  shared hard limit for macOS, CPU, GPU, models, frames, and caches.
- Use bounded queues and streaming. Never retain an entire decoded video or
  unbounded full-resolution frames in memory.
- Target normal processing peak RSS below 10 GB and investigate any swap.
- Evaluate cold and sustained performance; short peak throughput is not an
  adequate benchmark on a fanless machine.

## Pipeline

Use a two-pass design:

1. Analysis: decode a low-resolution proxy, sample frames adaptively,
   detect/track candidates, compute explainable interest signals, generate
   candidate shots, and plan a global camera path.
2. Render: decode the source once, apply the final path at source resolution,
   handle audio/timestamps, and encode the output. Use hardware acceleration
   when it improves iteration time without delaying the POC.

Do not repeatedly render full-resolution output while tuning the planner.
Compare plans with proxy previews and render full resolution only after the
decision path is selected.

## Auto-director architecture

Keep these layers separate and replaceable:

1. Spherical perception and seam-aware identity tracking.
2. Per-candidate evidence: initially person/object presence, track
   persistence, motion change, forward-motion prior, scene novelty, and
   composition.
3. Candidate shots: subject, group, and contextual/environment views.
4. Explainable shot-utility scoring.
5. Global planning with content value plus pan, acceleration, cut, switch,
   repetition, and minimum-dwell costs.
6. Optional temporal highlight selection.
7. Rendering.

Never use per-frame score argmax as the production director. Implement a
greedy strategy with hysteresis as a baseline and use dynamic programming or
a DAG/Viterbi-style global planner for the main approach.

Detector, tracker, scorer, and active-speaker implementations must sit behind
adapters. Ultralytics may be the initial POC backend, but it is not part of
the product identity and must remain replaceable.

## Correctness before optimization

- Establish geometry correctness with generated equirectangular grids and
  spherical markers before processing benchmark footage.
- Test pixel-to-yaw/pitch conversion, spherical distance, yaw unwrapping,
  seam crossings, poles, FOV, interpolation, and camera-path continuity.
- Use FFmpeg `v360` as the Phase 0 correctness reference. Runtime command
  semantics and performance must be regression-tested on the installed
  FFmpeg version.
- Do not start a Metal renderer, Core ML conversion, or zero-copy native
  pipeline until a measured bottleneck or faster path to evidence justifies
  it.

## Benchmarks

The public benchmark set is:

- Bellpuig on-board 360 — CC BY 3.0:
  <https://commons.wikimedia.org/wiki/File:Video_360_VR_on_board_de_Raul_Sanchez_en_Bellpuig.webm>
- Old Ghost Road mountain biking — CC BY-SA 3.0:
  <https://commons.wikimedia.org/wiki/File:3-mins-in-360_on_The_Old_Ghost_Road.webm>
- 360 Skiing May 2019 — CC BY 3.0:
  <https://commons.wikimedia.org/wiki/File:360_SKIING_MAY_2019.webm>

Compare at least:

1. Fixed-forward view.
2. Greedy motion/saliency with hysteresis.
3. The aegis global planner.

Evaluate subject/track continuity, spherical viewpoint error where labels
exist, angular velocity/acceleration/jerk, cuts and reversals, event coverage,
repetition, missed important events, peak memory, sustained throughput, and
blind pairwise viewer preference.

Benchmark media must not be committed to Git. Maintain a manifest with the
source page, direct download URL, creator, exact license, attribution text,
access date, SHA-256, media metadata, and intended benchmark role. Store local
assets under a gitignored path. Tests and normal commands must never download
assets implicitly.

Derived Old Ghost Road media must comply with CC BY-SA 3.0. Keep media-license
obligations separate from the repository's code license.

## Offline and data handling

- Setup/acquisition may use the network only through an explicit user action.
- Video analysis and rendering must run with no network, account, login, or
  telemetry.
- Never silently download models, packages, videos, music, or templates.
- Model weights and external assets require explicit manifests and checksums.
- Do not commit source footage, extracted user frames, faces, audio, GPS/IMU
  data, model weights, proxy media, or generated videos.
- Logs and decision traces should avoid personal data and absolute source
  paths. Temporary frames and identity embeddings must have a documented
  lifecycle and cleanup policy.

## Licensing

The intended repository license is Apache-2.0. Review licenses independently
for code, dependencies, model implementations, weights, datasets, footage,
audio, and generated media. A dependency's license is not replaced by the
repository license. In particular, isolate AGPL dependencies behind adapters
and do not assume an MIT/Apache repository license covers weights or training
data.

## Agent workflow

- Read relevant ADRs and design notes before changing architecture.
- Supervise delegated work with bounded waits; do not assume a still-running
  subagent or external job will report that it is stuck.
- Do not end the main turn with a final response while authorized delegated
  work is still active. Keep the turn alive with bounded waits, process
  completion notifications immediately, and continue integration without
  waiting for another user message.
- A delegated-work status update is commentary, not a stopping point. Send a
  final response only when the requested outcome is complete or progress
  genuinely requires a user decision, new authority, or an external-state
  change.
- For delegated work that does not incur usage-based charges, inspect its
  status and report meaningful progress to the user at least once every three
  minutes while it remains active.
- For delegated work that can continue generating usage-based charges, such
  as AWS services, inspect its status and report meaningful progress at least
  once every minute. If it is stalled or no longer useful, stop the chargeable
  work promptly or escalate the decision to the user.
- A progress report must say whether the work is advancing, waiting, blocked,
  or being recovered; a timer-only “still running” message is insufficient.
- Accepted decisions belong in `docs/adr/`; unsettled exploration belongs in
  `docs/design/`. Do not promote an assumption to an ADR without evidence.
- Add or update tests with behavioral changes.
- Preserve audio and timestamps unless the task or benchmark policy says to
  mute/remove them.
- Record hardware, OS, FFmpeg version, model/weights, input resolution, sample
  rate, interpolation, thermal state, elapsed time, peak RSS, and swap for
  performance claims.
- Preserve user changes and do not modify unrelated files.
- Do not add network-dependent tests or hidden asset downloads.

## Repository map

Start with `docs/README.md`. It is the canonical documentation index and
routes work by task.

- Current phase and next acceptance gate: `docs/status.md`
- Accepted decisions: `docs/adr/README.md`
- Current system design: `docs/design/system-overview.md`
- External claims and evidence: `docs/research/claim-ledger.md`
- Experiment protocols and results: `docs/experiments/README.md`
- Benchmark assets and licensing: `benchmarks/README.md`

Read only the documents relevant to the task, plus every ADR they link. If a
design document conflicts with an accepted ADR, follow the ADR and report the
conflict.

## Commands and layout

These commands have been verified on the reference machine:

- Geometry tests: `python3 -m unittest discover -s tests -v`
- Static FFmpeg `v360` evidence test: `tests/test_ffmpeg_v360_static.sh`
- FFmpeg/internal convention gate: `tests/check_ffmpeg_v360_conventions.py`
- Timestamped FFmpeg `v360` control test: `tests/test_ffmpeg_v360_dynamic.sh`
- Fixed-forward baseline test: `tests/test_fixed_forward_baseline.sh`
- Apple Vision synthetic gate: `tests/test_vision_frame_gate.sh`
- Apple Vision batch orchestration test: `tests/test_vision_batch_gate.sh`
- Apple Vision short-sequence tracking test:
  `tests/test_vision_tracking_gate.sh`
- Real/local Apple Vision tracking gate:
  `scripts/run_vision_tracking_gate.sh INPUT_VIDEO OUTPUT_DIR SOURCE_ID TRACK_ID START DURATION FPS VIEWPORT_YAW BOX_X BOX_Y BOX_W BOX_H`
- Multi-clip Apple Vision tracking aggregation test:
  `tests/test_vision_tracking_batch_gate.sh`
- Real/local multi-clip tracking aggregation:
  `python3 scripts/run_vision_tracking_batch_gate.py MANIFEST.json OUTPUT_DIR`
- Vision spherical-dedup report test:
  `tests/test_vision_spherical_dedup_report.sh`
- Real/local Vision spherical-dedup report:
  `scripts/run_vision_spherical_dedup_report.sh INPUT_BATCH_DIR OUTPUT_REPORT [GREEDY_TRACE]`
- Bounded Vision sequence test: `tests/test_vision_sequence_gate.sh`
- Real/local bounded Vision sequence evidence:
  `python3 scripts/run_vision_sequence_gate.py INPUT_VIDEO OUTPUT_JSON SOURCE_ID START DURATION FPS`
- First auto-directed slice orchestration test:
  `python3 -m unittest tests.test_auto_directed_slice -v`
- Three-output FFmpeg render-adapter test:
  `tests/test_render_slice_adapter.sh`
- Shot-static FFmpeg render-adapter test:
  `tests/test_render_slice_shot_static.sh`
- FFmpeg repeated-runtime-pose regression:
  `tests/test_ffmpeg_v360_runtime_pose_regression.sh`
- First auto-directed planning/bundle runner:
  `python3 scripts/run_auto_directed_slice.py VISION_SEQUENCE.json OUTPUT_DIR --source-id SOURCE_ID --width WIDTH --height HEIGHT --start START --duration DURATION [--config CONFIG.toml] [--render-adapter EXECUTABLE --render-mode {dynamic,shot_static_v360} --source-media INPUT_VIDEO]`
- Manual perception review validator:
  `python3 scripts/validate_review_annotations.py REVIEW.json`
- Local Vision review-pack test: `tests/test_vision_review_pack.sh`
- Shell syntax check: `sh -n scripts/*.sh tests/*.sh`

Current layout:

- `src/aegis360/`: dependency-free core geometry primitives
- `scripts/`: explicit synthetic-fixture and render helpers
- `tools/`: small native probes whose source and behavior are versioned
- `tests/`: unit and executable evidence tests
- `benchmarks/`: public asset manifest and attribution policy, not media
- `docs/`: decisions, design, research, experiment records, and history

Setup, end-to-end run, lint/format, and real-media benchmark commands remain
TBD. Do not invent them or silently download their dependencies.
