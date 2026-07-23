# First auto-directed slice protocol

Status: Real-media 30-second v1/v2 negative evidence and mechanically valid
cut-based v3 recorded; the project owner's qualitative review rejected v3, so
the unchanged series must not advance to 60 seconds.

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

Generated media and local source paths remain outside Git.

## Old Ghost Road 30-second run record

The first real-media rung used the deliberately selected zero-second prefix of
Old Ghost Road. The analysis cadence was 2 fps, yielding 60 decisions over 30
seconds. Generated evidence remains outside Git under the external artifact
root:

- `outputs/auto-directed/old-ghost-road-30s-v1/vision-sequence.json`
- `outputs/auto-directed/old-ghost-road-30s-v1/bundle/` (v1)
- `outputs/auto-directed/old-ghost-road-30s-v1/bundle-v2/` (v2)
- `outputs/auto-directed/old-ghost-road-30s-v1/bundle-v3/` (v3)

These are artifact-root-relative locations, not source-media paths. No local
source absolute path is recorded here.

### v1: invalid fallback scoring

The v1 trace selected `context:forward` for all 60 decisions and generated two
camera-path keyframes. This was not a meaningful directing result: a scoring
bug allowed the permanent context fallback to outrank observed subjects. The
bug was fixed in commit `cbe6d37` (`fix: keep context fallback below observed
subjects`). The v1 media is retained as negative integration evidence and must
not be used for qualitative review.

### v2: planning evidence passes, dynamic render evidence fails

After the scoring fix, v2 selected context for 5 decisions and a tracked
candidate for 55 decisions. It made one switch and emitted 40 camera-path
keyframes. The bundle is complete, and all three 30-second outputs decode with
the intended audio/video streams and aligned duration:
`fixed-forward.mp4`, `auto-directed.mp4`, and `debug-overlay.mp4`.

The renderer nevertheless failed the camera-path application gate. A
controlled comparison showed that dynamic FFmpeg `v360` output diverges from
an equal static-pose render after repeated timestamped pose commands. Thus the
files prove bounded real-media analysis, planning, bundle creation, decoding
and A/V preservation, but they do not prove that the rendered view follows the
planned poses. The v2 videos are not suitable for human review, and no paths
should be sent to the reviewer as review candidates.

### v3: cut-based camera application passes mechanical checks

The v3 run reused the same Vision evidence and planning configuration, but
grouped the decisions into two shots and rendered each with a static `v360`
pose. Fixed-forward is 30.000 seconds; auto and debug are about 30.040 seconds
with about 20 ms video/audio duration difference. All three decode with video
and audio. Sampled frames no longer exhibit the v2 repeated-command pose
divergence, so v3 is suitable for qualitative framing and cut review.

This is not smooth tracking evidence: the renderer deliberately holds one
representative pose per shot.

The project owner's qualitative review rejected v3. Fixed-forward lost the
bicycle and showed abnormal shaking near the end. Auto-directed also lost the
bicycle; its end shaking was somewhat better than fixed-forward but remained
uncomfortable, while the debug output's ending was worse. The reviewer also
identified the narrow framing as a likely major contributor: the selected FOV
ranged approximately from 44 to 93 degrees, with a median of approximately 76
degrees, so viewpoint errors and static holds may feel more severe than they
would in a wider view.

The selected track represents `attention_saliency`, not a verified bicycle
identity. Therefore this result must not be described as identity tracking or
as evidence that the director can retain the bicycle. The 30-second
qualitative gate failed, and this configuration series must not advance to the
60-second rung. Wider framing, subject/identity continuity, and the source of
the end shaking require separate diagnosis before another 30-second review
candidate is accepted.
