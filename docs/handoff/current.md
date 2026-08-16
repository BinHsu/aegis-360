# Current handoff

Updated: 2026-08-16T07:34:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 1da814a
Remote status: `origin/main` is 58626cb; Timeline/Packet v2 is committed locally
Working tree at checkpoint: only this handoff metadata differs from baseline

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer on a fanless M4 MacBook Air with 16 GB unified memory. The immediate
gate is visual pre-review of nine neutral scene-boundary packets.

## Accepted evidence

- Old Ghost Road conversation-group framing is owner accepted. It proves
  bounded group composition, not active-speaker or identity inference.
- Gaudeamus planned v5 is owner accepted: primary geometry -70/+5/120,
  audience +90/0/120, opening reaction suppressed, audience 109.5–119 and a
  natural return to titles.
- SmolVLM2 2.2B MLX BF16 is accepted only as a bounded group-vs-not-group
  gate. Fine context, mouth-motion and orientation fields are unusable.
- SmolVLM2 500M is rejected for planner integration; do not resume tuning it.

## Last completed milestone

Candidate-scoped availability and relative editorial gain are now separate,
closed evidence. Reaction plan v4 requires exact checksums for grid, roles,
reaction intervals, candidate availability and reaction-view gain:

- availability is bound to exact checksummed config and context grid;
- intervals are candidate-specific and ordered;
- an unlisted candidate has no implicit availability;
- reaction plan schema v4 binds and validates all five evidence artifacts;
- gain can only mark an exact declared event `promote` or `abstain`;
- current/proposed candidates derive from role evidence, not reviewer output;
- unreviewed gain defaults to abstain;
- renderer validation rebuilds the unique plan and rejects altered segments;
- primary geometry comes from role evidence, not a mutable segment reason;
- nonzero source windows use absolute `atrim` boundaries;
- legacy plan v1–v3 validation remains readable but cannot bypass v4 building.

Gaudeamus `promote` reproduces the owner-accepted three segments. Hundra
`abstain` produces one primary-only segment. Both renderer replays are decoded-
identical to their accepted references for video and audio.

The new reaction pre-review gate rebuilds v4 evidence, checks equal-lineage
trace/encoder/probe/audio contracts, and hashes decoded streams. Promote must
produce a distinct video with at least 8 degrees and 2 seconds of declared
difference; abstain must decode identically. Both real cases pass. The report
explicitly retains the need for visual editorial review.

Gain schema v2 now requires model ID/SHA for `local_vlm` and explicit nulls for
human review. V1 is rejected for new plans because its model provenance was
incomplete. Owner v2 artifacts reproduce Gaudeamus promote and Hundra abstain;
their new plan/render/pre-review lineages pass.

The installed SmolVLM2 2.2B pairwise adapter is rejected. Under one four-frame,
temperature-zero, decision-only protocol it returned abstain for both cases.
Gaudeamus should promote, so the result cannot reject always-abstain. Runs used
6.21 GB MLX peak and zero swap. Do not prompt-tune these two labels.

ADR 0010 restores the original automatic goal. Human gain decisions are
benchmark labels only. Product flow is cheap full-video signals, a sparse
checksummed event timeline, bounded before/during/after semantic packets, then
an explainable global planner with final authority. Per-frame VLM review and
user approval of every event are rejected.

Event Timeline v1 is implemented as an exact, checksummed derivation of the
context-view grid, editorial roles, reaction intervals and candidate-scoped
availability. It emits stable reaction-candidate IDs, retains original and
window-clipped boundaries, and records availability at onset and throughout
the event. It contains no owner promote/abstain answer, geometry, paths,
pixels, audio, names or identity. Validation rebuilds the complete document.

Real execution emits two Gaudeamus candidates and one Hundra candidate. The
Gaudeamus opening has no proposed view at onset and only 11.5–15.0 overlap;
its ending has availability at onset and 109.5–119.0 overlap. Hundra has full
217.5–226.5 availability. This schedules review; it authorizes no edit.

Event Review Packet v1 binds the exact timeline and grid. Each event schedules
before, early, midpoint, late and after anchors; out-of-window context is
explicitly null. Current view is always scheduled, while the proposed view is
listed only inside its availability intervals. The durable manifest contains
no media or answer and requires temporary rendered media to be deleted after
adapter completion. Three real packets reproduce the expected availability
differences without leaking owner labels.

The transient runner revalidates lineage, resolves only grid-owned geometry,
renders no more than ten silent 384x216 frames, invokes an argv-only adapter
and always leaves the temporary-directory scope afterward. A real Gaudeamus
run produced seven nonempty frames in 0.51 seconds; both a mistaken diagnostic
failure and the corrected pass cleaned their temporary media.

Event Semantic Evidence v1 allows only packet-bound closed observations or
strict claim-free abstention. It cannot emit confidence, free text, identity,
geometry, candidates, edit decisions or renderer commands. Model ID/SHA and
exact config/packet hashes are mandatory.

Event Candidate Utility v1 applies a checksummed, tunable policy and retains
separate relevance, visibility, temporal and relationship components. It does
not select a view. Abstention keeps current eligible at neutral utility and
makes proposed ineligible. Sparse Global Event DP v1 then optimizes ordered
events with minimum advantage/dwell plus two-way fixed switch, grid-derived
spherical angular and cross-event repetition costs. It does not yet emit a
continuous path. Global Camera Segments v1 covers the full window with primary
and overlays a selected proposal only on exact timeline availability.

FFmpeg scene evidence at 2 fps/320px plus score floor 0.4 and 10-second NMS
retains nine visually plausible Old Ghost Road boundaries and zero Bellpuig
candidates. Full 5K VP9 Skiing decode did not finish in the bounded session;
use a reusable proxy or bounded window, not another full-decode retry.

Event Timeline v2 fuses overlapping cheap-signal review windows. Scene-bearing
events keep all four declared candidates and no roles. Nine real Old Ghost Road
events each produce an eight-frame before/after Packet v2. A real runner smoke
test passes 8/8 and deletes its temporary media.

## Held-out benchmark

Hundra is a checksummed CC BY-SA 4.0 1920x960 ERP held-out source. Its
217.5–226.5 reaction candidate is owner-rejected because the primary procession
view presents the bilateral audience better than the flag/tent-obscured
proposal. Incidental minors remain ineligible subjects. Exact provenance lives
in the benchmark manifest and experiment record.

## Repository state

- Expected branch: `main`; content baseline is `1da814a` and remote is `58626cb`.
- Only the handoff metadata should differ from the content baseline.
- Media, models and generated artifacts are external and gitignored.
- Git history is the archive; current handoff/status replace stale state.

## Verified

- `python3 -m unittest discover -s tests -q`: 360 tests pass.
- Scene-event/NMS targeted tests: 4 pass.
- Timeline/Packet v2 targeted tests: 5 pass.
- Gaudeamus v4 and accepted v6 decoded video/audio hashes match exactly;
  Hundra v4 abstain and primary decoded video/audio hashes match exactly.

## Rejected

- Broad any-view live-scene evidence cannot authorize a specific reaction view.
- Missing candidate availability must fail closed to primary.
- Do not treat audio classification as direction, role or editorial utility.
- Do not use +90 (flag-obscured) or -90 (tent-obscured) as Hundra reaction
  geometry without new evidence.
- Do not claim the legacy fixed/auto pre-review gate passed reaction bundles.
- Do not equate reduced occlusion or a different composition with improved
  reaction evidence; the proposed view must beat the current view editorially.
- Do not integrate the SmolVLM2 2.2B pairwise adapter or count its Hundra
  abstention as a pass; it failed the Gaudeamus positive.
- Do not consume reaction-view-gain v1 for new plans; use provenance-complete v2.

## Pending

- Push Timeline/Packet v2 after its metadata commit.
- Visually pre-review nine neutral packets; request owner labels only for
  survivors that are materially distinct and relevant.

## Next commands

Set `AEGIS_DATA_DIR` to the external artifact root. Validate the checkpoint:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_handoff.py
git diff --check
git status --short
```

## External artifacts

The external artifact root is configured by `AEGIS_DATA_DIR`; never commit it.

- `outputs/candidate-availability/gaudeamus-audience-v1/availability.json`
- `outputs/reaction-shot-plans/gaudeamus-full-owner-rule-v5-candidate-availability-trace/plan.json`
- `outputs/reaction-preview/gaudeamus-full-planned-540p-v6-p0-rebind/`
- `outputs/sound-events/hundra-full-apple-v1/events.json`
- `outputs/reaction-intervals/hundra-full-apple-v1-threshold-p5/intervals.json`
- `outputs/context-view-grids/hundra-210-226p5-declared-v1/grid.json`
- `outputs/editorial-view-roles/hundra-210-226p5-v1/roles.json`
- `outputs/candidate-availability/hundra-audience-v1/availability.json`
- `outputs/event-timelines/old-ghost-road-multi-signal-v2/timeline.json`
- `outputs/event-review-packets/old-ghost-road-multi-signal-v2/event-multi-*.json`
- `outputs/reaction-view-gain/{gaudeamus,hundra}-owner-v2/gain.json`
- `outputs/reaction-shot-plans/{gaudeamus-full-owner-rule-v7-gain-v2,hundra-210-226p5-v3-gain-v2-abstain}/plan.json`
- `outputs/reaction-preview/gaudeamus-full-{primary,planned}-540p-v8-gain-v2/`
- `outputs/reaction-preview/hundra-210-226p5-{primary,planned}-v3-gain-v2/`
- `outputs/reaction-pre-review/{gaudeamus-v8-gain-v2,hundra-v3-gain-v2}/report.json`
- `outputs/reaction-view-gain/{gaudeamus,hundra}-smolvlm2-2p2b-pairwise-v1/gain.json`
- `outputs/event-timelines/{gaudeamus-reaction-v1,hundra-reaction-v1}/timeline.json`
- `outputs/event-review-packets/{gaudeamus-reaction-v1,hundra-reaction-v1}/event-reaction-*.json`

## Milestone repository files

- `docs/adr/0010-sparse-event-semantic-planning.md`
- `src/aegis360/event_timeline.py`
- `scripts/build_event_timeline.py`
- `tests/test_event_timeline.py`
- `docs/experiments/event-timeline-v1-2026-08-16.md`
- `src/aegis360/event_review_packet.py`
- `scripts/build_event_review_packet.py`
- `tests/test_event_review_packet.py`
- `docs/experiments/event-review-packet-v1-2026-08-16.md`
- `src/aegis360/review_media.py`
- `scripts/run_event_review_adapter.py`
- `tests/test_review_media.py`
- `docs/experiments/transient-event-review-media-2026-08-16.md`
- `src/aegis360/event_semantics.py`
- `src/aegis360/local_event_semantics_schema.py`
- `scripts/bind_event_semantics.py`
- `tests/test_event_semantics.py`
- `docs/design/event-semantic-evidence.md`
- `src/aegis360/event_utility.py`
- `scripts/build_event_candidate_utility.py`
- `tests/test_event_utility.py`
- `config/event-utility-policy-v1.json`
- `src/aegis360/global_event_planner.py`
- `scripts/build_global_event_plan.py`
- `tests/test_global_event_planner.py`
- `config/global-event-planner-policy-v1.json`
- `src/aegis360/global_camera_segments.py`
- `scripts/build_global_camera_segments.py`
- `tests/test_global_camera_segments.py`
- `src/aegis360/{scene_events,scene_change_candidates}.py`
- `scripts/{run_ffmpeg_scene_events,build_scene_change_candidates}.py`
- `docs/experiments/ffmpeg-scene-change-events-2026-08-16.md`
- `src/aegis360/{multi_signal_timeline,multi_signal_review_packet}.py`
- `scripts/build_multi_signal_{timeline,review_packet}.py`
- `docs/experiments/multi-signal-timeline-review-v2-2026-08-16.md`
- `docs/experiments/apple-sound-reaction-gate-2026-08-15.md`
- `docs/status.md`, `docs/handoff/current.md`

## Active agents

No delegated work is active or required to resume this checkpoint.

## Safety and claims

- Keep media, generated pixels, audio, model weights and absolute source paths
  out of Git and durable privacy-safe JSON.
- Analysis/rendering remain offline; acquisition requires explicit authority.
- Preserve bounded queues and the 16 GB unified-memory constraint.
- Geometry continuity, faces and mouth motion do not establish identity or
  proven speech.
- No delegated work is active.
