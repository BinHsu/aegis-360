# First auto-directed slice protocol

Status: Protocol and synthetic contract evidence only; no real-media result or
quality claim.

## Question

Can one bounded real-media prefix pass through the current sequence, interest,
greedy, camera-path and render boundaries and produce three mechanically valid,
directly comparable review artifacts?

This gate tests integration and exposes bad camera behavior quickly. It does
not establish that the chosen viewpoint is interesting, that motion is
comfortable, or that greedy directing is better than fixed-forward.

## Current executable boundary

The implemented, synthetic-tested chain is:

1. ingest bounded Apple Vision sequence JSON;
2. convert viewport candidates to spherical observations and deduplicate within
   each sampled timestamp;
3. associate same-type candidates over time by spherical distance, with a
   bounded missing-frame grace period and a permanent forward/context fallback;
4. score presence, persistence, composition and forward prior without treating
   detector confidence as editorial interest;
5. apply the versioned greedy-with-hysteresis configuration;
6. convert selected decisions into a sparse, clip-relative camera path; and
7. atomically persist trace, resolved config, camera path and artifact manifest.

The orchestrator also defines an explicit render-adapter request for
`fixed-forward.mp4`, `auto-directed.mp4` and `debug-overlay.mp4`. The existing
orchestrator test uses a fake adapter to prove contract and failure behavior.
The FFmpeg adapter separately produces all three decodable, synchronized
outputs from a two-second synthetic ERP A/V fixture. Neither test proves
real-media rendering or viewing quality; that is the next gate.

## Fixed first run

Use Old Ghost Road for the first 30-second rung because it is an accepted
monoscopic ERP POC asset and does not require Bellpuig's projection override.
Record the exact start timestamp before running. The first run may use zero
only if the operator deliberately selects it; do not move the start after
viewing results without creating a new configuration series.

Use:

- the source hash from `benchmarks/manifest.toml`;
- `config/greedy-first-slice-v1.toml` unchanged across the series;
- identical source, start, duration, viewport dimensions, output dimensions,
  frame rate, interpolation and audio policy for all three outputs;
- one analysis result and one auto camera path shared by auto-directed and
  debug-overlay;
- a new output bundle path; the runner must not overwrite an earlier bundle.

Do not tune weights or hysteresis after inspecting the 30-second output and
then call the longer output the same series. Any tuning change creates a new
configuration identifier and restarts comparison at 30 seconds.

## Duration ladder

Follow `duration-ladder-protocol.md` and
`benchmarks/duration-ladder.toml`:

| Rung | Primary gate |
|---:|---|
| 30 s | framing, obvious render defects, abrupt motion and implausible switches |
| 60 s | dwell, switch timing and preliminary viewing comfort |
| 180 s | continuity, repetition, event coverage and accumulated drift |
| 300 s | long-view fatigue plus sustained memory and throughput |

Old Ghost Road and Bellpuig are eligible for 30/60/180 seconds. Skiing is
eligible for all four rungs and is the sustained-performance asset. Bellpuig
requires its documented projection override and is not geometry ground truth.

Every longer rung must share the common start and immutable configuration so
the shorter run is its comparable prefix. Do not request a 300-second render
from a source shorter than that rung.

## Procedure

1. Validate the static ladder contract with
   `python3 scripts/validate_duration_ladder.py`.
2. Run the bounded sequence analysis for the selected source/start/duration and
   retain only privacy-safe persisted evidence. Record sample cadence and
   adapter/backend provenance.
3. Run the auto-directed slice orchestrator with the versioned config and the
   production render adapter.
4. Require the bundle to contain `trace.json`, `config.json`,
   `camera-path.json`, `artifacts.json` and all three MP4 outputs.
5. Mechanically verify each MP4 is decodable and matches the intended duration,
   dimensions, frame rate/audio policy and timestamp behavior.
6. Verify debug-overlay uses the same camera path and trace as auto-directed.
7. Inspect trace and camera metrics for empty choices, fallback-only behavior,
   rapid switches, reversals, extreme angular steps and multi-segment jerk
   discontinuities. Record measurements without inventing a comfort threshold.
8. Only after the mechanical gate passes, give the project owner the complete
   absolute paths for the three videos and a short review checklist.
9. Record the review separately from automated checks. A pass permits the next
   duration rung; a configuration change restarts the series.

## Acceptance criteria

Mechanical acceptance requires:

- all required artifacts exist and the manifest reports a complete run;
- the three videos use the same source interval and render/audio settings;
- auto-directed and debug-overlay share an identical plan;
- outputs decode successfully with no material A/V duration mismatch;
- trace/config contain no source-media absolute path or pixels;
- selected candidates always resolve to valid spherical camera geometry; and
- any renderer error or missing artifact fails the bundle rather than leaving
  a misleading complete result.

Qualitative acceptance is explicitly human:

- fixed-forward and auto-directed can be compared over identical content;
- the auto view does not show obvious bad framing, unexplained jumps, rapid
  reversals or implausible switches; and
- the debug overlay explains the selected candidate and switch decision well
  enough to diagnose a failure.

A 30-second qualitative pass only unlocks the 60-second rung. It is not a
claim of comfort, narrative quality, event coverage, sustained performance or
superiority over the baseline.

## Required run record

Record commit/worktree identity, asset id and hash, common start, duration,
configuration id and resolved config, OS/hardware/FFmpeg, Vision provenance,
sample cadence, projection decision, render settings, audio policy, artifact
paths, mechanical probes, camera/switch metrics, reviewer outcome and all
limitations. Performance claims additionally follow
`m4-air-sustained-performance.md`.

Generated media and local source paths remain outside Git. Do not add a result
section until a real run has completed.
