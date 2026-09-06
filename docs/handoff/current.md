# Current handoff

Updated: 2026-09-06T09:30:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: a334ba6
Remote status: `origin/main` at `a334ba6` before this checkpoint
Working tree at checkpoint: typed packet/relevance/continuity/planner integration plus current docs

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless
MacBook Air M4 with 16 GB unified memory. The immediate gate is a complete,
typed and fail-closed Skiing plan before any further render.

## Read first

1. `AGENTS.md`
2. `docs/status.md`
3. `docs/design/event-semantic-evidence.md`
4. `docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`
5. ADR 0010, then ADR 0006 and ADR 0011

No chat transcript, agent session or vendor-specific memory is required.

## Last completed milestone

- Typed story timelines emit review packet v2 with explicit typed lineage;
  legacy packet v1 output and its fixed digest remain unchanged.
- Segment relevance explicitly accepts only packet v1/v2. Typed packet
  abstention feeds the existing neutral candidate-utility contract.
- Causal continuity accepts typed timeline/packet lineage. A typed one-segment
  timeline legally produces zero edges; legacy timelines still require at
  least two segments.
- `aegis360.typed-global-story-plan.v1` consumes only typed timelines, complete
  ordered candidate utilities, complete continuity utility, grid and policy.
- Planner input contracts are closed over root/nested shapes, lineage,
  producer authority, candidate order, finite totals and safe IDs.
- Observed segment utility must make every grid candidate eligible; abstention
  makes none eligible and keeps every total neutral.
- DP applies one edge cell and one fixed plus spherical-angular cost per
  actual switch. Closing hold and abstention retain the incoming candidate.
- Any segment or edge abstention sets `production_eligible=false`.
- The planner never emits renderer commands.

## Repository state

- Expected branch: `main`; baseline and remote were `a334ba6`.
- Generated evidence is external and must remain untracked.

## Verified

- Targeted vertical integration: 53 tests pass.
- Full suite: 493 tests pass.
- `git diff --check`: passes.
- Media, models, review pixels and generated artifacts are external only.
- Temporary five-sample semantic review pixels were deleted.

## Real replay

External root:
`$AEGIS_DATA_DIR/outputs/continuous-onset/skiing-v1`

The 380–395 acquisition contains 59 normalized frame-difference samples. Its
single proposed onset at 386.25–386.75 is independently classified
`no_semantic_change`: the ski area, lift, slope and skiers persist while
relative motion, a near object and the stitch band change.

The typed boundary artifact therefore authorizes zero boundaries and the typed
timeline contains one segment. The new vertical path produces:

- review packet v2 SHA `6792ed35cbdbb11600195e562bb92197d076aaeb2fdf792790a1b3ff97a7d339`;
- abstain relevance SHA `37f7bb687be6eea19d5ed6d305c77e2b9e91e919453509943e1a3e68ab7874f2`;
- neutral utility SHA `e7aa3eb45fd2e986363365c86603b9b45675e75351b1373bdcbbb351051860d4`;
- zero-edge continuity evidence SHA `02ba0363ec4116540ce48071fd70a19ae02f08cafe624bfb395aae4751d9898b`;
- zero-edge transition utility SHA `3749672e633af1f4f32270f6a9039db4445632abd9dc155793874b7a0d143277`;
- typed plan SHA `29b58c779ad6ae861283da87a669f56ec692cdb510c5205387a28d00a16482a8`.

The plan keeps `context:cardinal:0` over 380–395 with objective 0, no edge,
no switch and no cost. It is deliberately not production eligible. No video
was rendered and no owner review is pending.

## Policy-v1 caveats

- `chapter_boundary` and `within_chapter_cut` retain different labels but use
  the same numeric switch gate.
- `minimum_dwell_seconds` is the duration of the destination segment, not
  accumulated time since the last switch.
- `minimum_advantage` prunes locally before fixed/angular costs.

Do not change these meanings without a measured policy-v2 experiment.

## Rejected

- The old hand-authored 390-second split is pilot edit timing, not source
  semantic-boundary evidence.
- The 386-second motion burst is not a story change.
- The typed replay does not cover 395–415 or the full Skiing source.
- Empty continuity for a one-segment timeline is not an abstained edge and
  must not be replaced with fabricated observations.
- A retained default view under abstention is not evidence that the view is
  editorially best.

## Pending

- Checkpoint and push this typed planner integration.
- Extend the same acquisition/evidence chain over 395–415 seconds.
- Obtain complete observed segment-view relevance before rendering.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After the checkpoint is pushed, continue with bounded 395–415 acquisition
under the existing frame-difference v2 contract. Build typed boundary and
timeline artifacts from that evidence; do not reuse the legacy 390-second
split. Produce complete segment-view evidence before invoking a renderer.

## External artifacts

Set `AEGIS_DATA_DIR` locally. Durable generated artifacts are under
`outputs/continuous-onset/skiing-v1/`; exact hashes are listed above and in
the experiment record. Never commit that directory.

## Main repository files in this checkpoint

- `src/aegis360/story_segment_review_packet.py`
- `src/aegis360/segment_view_relevance.py`
- `src/aegis360/causal_continuity_evidence.py`
- `src/aegis360/typed_global_story_planner.py`
- `scripts/plan_typed_global_story.py`
- corresponding tests under `tests/`
- `docs/design/event-semantic-evidence.md`
- `docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`
- `docs/status.md`, `docs/handoff/current.md`, `docs/README.md`, `README.md`

## Active agents

No delegated work remains active. All completion packets were integrated and
independently rechecked by the main agent.

## Safety and claims

- Never commit media, frames, audio, model weights, identity embeddings or
  absolute local source paths.
- Analysis/rendering remain offline; downloads require explicit authority.
- Keep queues and memory bounded for the 16 GB unified-memory machine.
- Geometry, faces and mouth motion do not establish identity or speech.
- Git history is the archive; status and handoff contain current state only.
- Stop for user input only on a real decision, new authority or external
  dependency. Otherwise update this handoff at each milestone and continue.
