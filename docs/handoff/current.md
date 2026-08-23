# Current handoff

Updated: 2026-08-24T06:10:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 224f520
Remote status: `origin/main` is 224f520 before planner v2
Working tree at checkpoint: planner v2, CLI, tests and current evidence docs only

## Objective

Build an offline 360-video auto-director for ordinary viewers on the fanless M4/16 GB machine. The immediate
gate is corrected Skiing semantic-boundary lineage before another render.

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

Candidate availability and editorial gain are separate closed evidence; plan v4 checks grid, roles,
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

Gaudeamus `promote` reproduces the accepted segments; Hundra `abstain` stays primary. Both are decoded-
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

Event Timeline v1 derives from the grid, roles, reaction intervals and candidate-scoped
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

The transient runner validates lineage/geometry, renders at most ten silent 384x216 frames, invokes an adapter
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

Story Packet v1 uses up to six far/near/boundary anchors over about 30 seconds.
Each temporary image is a 2x2 four-cardinal composite, so the adapter sees at
most six images/24 source viewports. Whole-video position and adjacent-event
summaries are durable; pixels are deleted after adapter exit. A real 0008 run
passes 6/6 768x432 probes and runner cleanup. Width/height options must precede
positional inputs because the adapter command uses `argparse.REMAINDER`.

Closed story semantics separate structural role, narrative function, change
type and viewer value. Observed labels must be complete; abstention is all-
unknown. Five agent source-context labels cover two chapter boundaries, two
within-chapter cuts and one ending. They are not owner ground truth and do not
select views or edits. Symbolic constraints now map chapter to change/reset,
within-chapter to continuity/retain and ending to closing/retain. Viewer value
maps to coverage priority. The real five-event artifact SHA is
`5e88ff336fe96b676265a93ad04dfbbed3f68dfd34b7d356f5431d6aee2c542c`;
it applies no numeric costs and selects no candidate.

Exact story contact sheets prove event-wide view relevance invalid: before and
after often require different directions, and far context crosses later cuts.
The segment timeline partitions 26 boundaries into 27 positive-duration scopes
(1.4–25.1 seconds), SHA
`c54aaafe55e17126c4004bd9b5c949eca6ab17a216d71e640c7f5bc8edc3967e`.
Segment packets sample 20/50/80% without crossing boundaries; real 0010 passes
3/3 composite probes and cleanup. Relevance labels 0007/0010/0021 observed
stable primaries; 0020/0026 abstain. They are agent labels, not owner truth.

The symbolic planner keeps cardinal 0 throughout 53–95.6 and switches from
cardinal 0 to 1 at the 168.4 waterfall chapter in 163.5–174.4. Owner accepts a
destination-first story hint only if complete chapter starts and ends make the
time excursion legible. ADR 0011 records the fail-closed rule: current local
labels cannot authorize reordering, so chronology remains the fallback.

Whole-film chapter-map v1 accounts every retained scene boundary by exact
event/signal/timestamp and derives gap-free chapters. The independent
eligibility gate requires exact-map qualification, at least two chapters and a
later destination. Abstain or missing destination returns closed failure; a
pass only permits planning and selects no interval, view or renderer command.
No complete Old Ghost Road map has been claimed. Exact-signal story packet v1
now separates the fused 24.5/25.9-second boundaries while retaining six bounded
cardinal composites and transient deletion. All 26 external JSON manifests
exist without pixels. Owner accepts the unchanged original's eight marked
chapters as natural. A new source-verified lineage passes eligibility while
preserving the prior abstain artifact. Prefix v1 is perceptually rejected; v2
is intelligible only after intent disclosure and cannot count as blind proof.
A 35-second neutral Skiing pilot and hidden baseline share exact contracts.
The sealed-key result is `1 / partial_focus`, confusion false: owner saw
skiing, scenery, other skiers and expected closer action, but not the hidden
gathering-to-terrain/shared-departure relationship. Edit legibility passes;
full-intent communication does not. Baseline then wins pairwise direction and
watchability due to lift/skier causal cues and smoother transition. Generic
segment gain marks A ineligible and maps deterministically to baseline.

Persistent story DP requires complete ordered per-segment utility. It retains
DP state on abstain/closing, and charges one fixed plus spherical-angular cost
only when the persistent candidate changes. Equal-utility and cost-deficient
90-degree switches fail. Real Skiing v2 retains c0/c0 with or without continuity; continuity raises objective 3.5→5.5 but is not decision-critical.

## Held-out benchmark

Hundra is a checksummed CC BY-SA 4.0 1920x960 ERP held-out source. Its
217.5–226.5 reaction candidate is owner-rejected because the primary procession
view presents the bilateral audience better than the flag/tent-obscured
proposal. Incidental minors remain ineligible subjects. Exact provenance lives
in the benchmark manifest and experiment record.

## Repository state

- Expected branch: `main`; milestone parent is `7c67a03`.
- This checkpoint adds continuity-aware persistent story planner v2.
- Media, models and generated artifacts are external and gitignored.
- Git history is the archive; current handoff/status replace stale state.

## Verified

- `python3 -m unittest discover -s tests -q`: 425 tests pass.
- Bounded planner/render targeted tests: 6 pass.
- Scene-boundary renderer contract test: 1 pass.
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
- Do not restore 2 fps alone, floor 0.4 or 10-second scene NMS; each loses
  source-verified story boundaries.

## Pending

- Replace the late 390-second Skiing boundary near the continuous 385.5–386-second
  semantic transition; rebuild evidence and do not render stale lineage.

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

- `outputs/scene-change-candidates/old-ghost-road-v5-pyramid-high-recall.json`
- `outputs/event-timelines/old-ghost-road-multi-signal-v5-pyramid-high-recall/timeline.json`
- `outputs/story-segment-timelines/old-ghost-road-pyramid-v1/timeline.json`
- `outputs/segment-view-relevance/old-ghost-road-agent-v1/*.json`
- `outputs/blind-intent-pilots/skiing-a-v1/{blind-intent-A,baseline}.mp4`
- `outputs/chapter-map-reviews/old-ghost-road-agent-v1/original-with-agent-chapters.mkv`

## Milestone repository files

- `docs/adr/{0010-sparse-event-semantic-planning,0011-fail-closed-chapter-aware-foreshadow}.md`
- `docs/design/event-semantic-evidence.md`
- `src/aegis360/{whole_film_chapter_map,chapter_map_foreshadow_eligibility}.py`
- `scripts/{build_whole_film_chapter_map,assess_chapter_map_foreshadow}.py`
- `src/aegis360/segment_editorial_gain.py`, `scripts/bind_segment_editorial_gain.py`, `tests/test_segment_editorial_gain.py`
- `docs/experiments/whole-film-chapter-map-v1-2026-08-23.md`
- `src/aegis360/scene_boundary_story_packet.py`, `scripts/build_scene_boundary_story_packet.py`
- `src/aegis360/prefix_foreshadow_plan.py`, `scripts/plan_prefix_foreshadow.py`
- `docs/experiments/{prefix-foreshadow-plan-v1,blind-director-intent-protocol-v1}-2026-08-23.md`
- `docs/status.md`, `docs/handoff/current.md`

## Active agents
No delegated work is active or required to resume this checkpoint.

## Safety and claims
- Keep media, pixels, audio, weights and absolute source paths out of Git.
- Analysis/rendering remain offline; acquisition requires explicit authority.
- Preserve bounded queues and the 16 GB unified-memory constraint.
- Geometry, faces and mouth motion do not establish identity or proven speech.
- Temporal reordering remains disabled until the ADR 0011 gate is implemented.
