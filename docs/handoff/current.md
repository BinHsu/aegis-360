# Current handoff

Updated: 2026-08-15T21:36:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: e3cafe2
Remote status: `origin/main` is 4126aa1; gain-v2/model rejection is committed locally
Working tree at checkpoint: only this handoff metadata differs from baseline

## Objective

Build an offline, camera-agnostic 360-video auto-director for an ordinary
viewer on a fanless M4 MacBook Air with 16 GB unified memory. The immediate
gate requires an owner decision: keep owner-authored relative gain for the POC,
or authorize evaluation/acquisition of a different local VLM.

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

## Held-out benchmark

The supplemental source is `Hundra knektars marsch på Forum Vulgaris`:

- source page: <https://commons.wikimedia.org/wiki/File:Hundra_knektars_marsch_p%C3%A5_Forum_Vulgaris.webm>
- creator: Jan Ainali; own work; CC BY-SA 4.0;
- 1920x960 exact monoscopic ERP, 227.232 seconds, VP8/Vorbis;
- SHA-256: `63746e59215f72f1d94003b1b7921ac01b87f02048037d2e606fb07bbff1c61c`;
- 110751744 bytes;
- incidental minors are background and must not become eligible subjects;
- excluded from the duration ladder.

Apple SoundAnalysis finds one threshold-qualified interval at 217.5–226.5:
five supporting windows, applause peak 0.782600 and clapping peak 0.801312.
Contact-sheet review establishes the camera as part of the moving procession.
For the bounded 210–226.5 window, yaw 0/pitch 0/HFOV 110 is primary and yaw
-45/pitch 0/HFOV 110 centers the left roadside audience. The +90 direction is
flag-obscured and -90 is tent-obscured.

The rejected v3 plan contains two segments, but v4 records owner `abstain` and
contains only primary 210–226.5. Its 248 video and 516 audio frames hash exactly
the same after decoding as the existing primary render. This prevents the
rejected cut without disabling the accepted Gaudeamus reaction edit.

The existing `check_render_pre_review.py` consumes legacy fixed/auto bundles,
not reaction previews. Do not claim that gate passed; add a reaction-specific
gate after the owner decision unless a defect is found first.

## Repository state

- Expected branch: `main`; content baseline is `e3cafe2` and remote is `4126aa1`.
- Only the handoff metadata should differ from the content baseline.
- Media, models and generated artifacts are external and gitignored.
- Git history is the archive; current handoff/status replace stale state.

## Verified

- `python3 -m unittest discover -s tests -v`: 331 tests pass.
- Candidate availability targeted tests: 3 pass.
- Relative-gain/plan/renderer targeted tests: 10 pass.
- Hundra source SHA-256 and metadata match the manifest.
- Both Hundra peers share dimensions, renderer settings, frame count and audio
  frame count.
- Representative decoded frames were inspected before and after owner review;
  the denser replay confirms the owner's rejection.
- Gaudeamus v4 and accepted v6 decoded video/audio hashes match exactly;
  Hundra v4 abstain and primary decoded video/audio hashes match exactly.
- Real pre-review reports pass for Gaudeamus promote and Hundra abstain.

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

- Push the gain-v2/model-rejection milestone after its metadata commit.
- Owner decision: retain human comparative review for POC speed, or authorize a
  different local VLM evaluation/acquisition. Do not tune the rejected model.

## Next commands

Set `AEGIS_DATA_DIR` to the external artifact root. Validate the checkpoint:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_handoff.py
git diff --check
git status --short
```

Rejected comparison retained for reproduction, not renewed owner review:

```sh
open "$AEGIS_DATA_DIR/outputs/reaction-preview/hundra-210-226p5-primary-v1/video.mp4"
open "$AEGIS_DATA_DIR/outputs/reaction-preview/hundra-210-226p5-planned-v1/video.mp4"
```

Observed difference: both begin with the same forward procession view. At 7.5
seconds into the excerpt (source 217.5), planned hard-cuts 45 degrees left. It
removes the right-side flag but introduces a left-side tent and loses the more
complete bilateral audience response. Keep primary; do not renew this cut.

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
- `outputs/reaction-shot-plans/hundra-210-226p5-v1/plan.json`
- `outputs/reaction-preview/hundra-210-226p5-{primary,planned}-v1/`
- `outputs/reaction-view-gain/{gaudeamus,hundra}-owner-v2/gain.json`
- `outputs/reaction-shot-plans/{gaudeamus-full-owner-rule-v7-gain-v2,hundra-210-226p5-v3-gain-v2-abstain}/plan.json`
- `outputs/reaction-preview/gaudeamus-full-{primary,planned}-540p-v8-gain-v2/`
- `outputs/reaction-preview/hundra-210-226p5-{primary,planned}-v3-gain-v2/`
- `outputs/reaction-pre-review/{gaudeamus-v8-gain-v2,hundra-v3-gain-v2}/report.json`
- `outputs/reaction-view-gain/{gaudeamus,hundra}-smolvlm2-2p2b-pairwise-v1/gain.json`

## Milestone repository files

- `benchmarks/manifest.toml`, `benchmarks/README.md`
- `benchmarks/view-grids/hundra-procession-reaction-v1.json`
- `benchmarks/candidate-availability/{gaudeamus,hundra}-audience-v1.json`
- `src/aegis360/candidate_availability.py`
- `src/aegis360/reaction_plan.py`
- `scripts/bind_candidate_availability.py`
- `scripts/render_reaction_shot_plan.py`
- `tests/test_candidate_availability.py`
- `tests/test_reaction_plan.py`
- `tests/test_reaction_renderer_contract.py`
- `benchmarks/reaction-view-gain/{gaudeamus,hundra}-owner-v2.json`
- `src/aegis360/reaction_view_gain.py`
- `scripts/bind_reaction_view_gain.py`
- `tests/test_reaction_view_gain.py`
- `src/aegis360/reaction_pre_review.py`
- `scripts/check_reaction_pre_review.py`
- `tests/test_reaction_pre_review.py`
- `src/aegis360/local_reaction_gain_schema.py`
- `scripts/run_mlx_vlm_reaction_gain.py`
- `tests/test_local_reaction_gain_contract.py`
- `docs/experiments/smolvlm2-2.2b-reaction-gain-gate-2026-08-15.md`
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
