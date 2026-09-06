# Project status

Status: typed continuous-onset planning is fail-closed; Skiing coverage remains bounded

## Current conclusion

The repository has an executable offline analysis-to-render architecture for
monoscopic equirectangular input on the M4/16 GB reference machine. It now
includes typed continuous-onset segmentation and a persistent numeric global
planner. The latest real Skiing replay correctly produces no cut and no render:
motion evidence at 386.25–386.75 seconds is not a semantic story change, while
observed 380–415 candidate-view evidence selects the existing cardinal-0
baseline, making another identical render unnecessary.

The complete 380–415 window now has observed candidate-view relevance and a
production-eligible plan. It retains the already preferred fixed-forward view,
so no redundant render is produced. This is a bounded directing pass, not a
whole-source result.

## Accepted evidence

- Public benchmark provenance and licensing are recorded; media, models,
  pixels and generated video remain outside Git.
- FFmpeg `v360` geometry, camera paths, audio/timestamp handling and mechanical
  render gates have synthetic and bounded real-media coverage.
- Old Ghost Road conversation-group framing is owner accepted. It proves
  bounded nonidentity group composition, not active-speaker inference.
- Gaudeamus planned v5 is owner accepted for one role-bound audience reaction.
- Hundra is a held-out rejection: its primary view beats the obscured reaction
  proposal.
- SmolVLM2 2.2B MLX BF16 is accepted only as a bounded group-vs-not-group
  gate; fine context, mouth-motion and orientation fields are unusable.
- Whole-video sparse events, closed semantic packets, typed boundaries,
  segment relevance, candidate utility, continuity utility and DP planning are
  separate checksummed authorities.
- Chronology remains the fallback. Temporal reordering is not authorized.

## Latest Skiing evidence

- The bounded acquisition covers source seconds 380–395 at 4 fps, 320-pixel
  grayscale proxy width and two FFmpeg threads: 59 normalized difference rows.
- A benchmark-only uncalibrated hysteresis policy proposes one review onset:
  uncertainty 386.25–386.5, support 386.5–386.75 seconds.
- Five exact four-cardinal samples show the same ski area, lift, slope and
  nearby skiers. The burst is relative motion/near-object/stitch-band change,
  classified `no_semantic_change`.
- The typed-boundary adapter rejects the onset with null effective time and
  authorizes zero boundaries.
- The typed 380–395 timeline therefore contains one complete segment.
- The authoritative continuous 380–415 acquisition contains 139 rows and
  preserves hysteresis across 395 seconds. It emits only the same rejected
  motion onset and forms one 35-second typed segment.
- Review packet v2 samples 387, 397.5 and 408 seconds. Independent review finds
  cardinal 0 clear/primary/stable; all other directions score lower.
- A one-segment timeline has zero adjacency edges. Continuity evidence and
  transition utility correctly contain empty edge lists.
- Typed global planning retains `context:cardinal:0` at objective 3.5 with no
  transition or cost. `production_eligible=true` and
  `renderer_command_emitted=false`; rendering is skipped because this is
  decision-identical to the fixed-forward baseline.

The exact artifact hashes are recorded in
`docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`.

## Planner contract

`aegis360.typed-global-story-plan.v1` accepts only the typed timeline route and
requires one closed utility per ordered segment plus complete continuity, grid
and policy inputs. It rejects malformed/extra structures, invalid lineage,
partial observed candidate coverage, and forged producer authority. Any
segment or edge abstention disables production eligibility.

Policy-v1 semantics are intentionally explicit:

- chapter and within-chapter labels share the same numeric switch gate;
- `minimum_dwell_seconds` means destination-segment duration, not accumulated
  time held since the previous switch;
- minimum advantage is a pre-cost local pruning rule;
- closing hold retains the incoming view;
- one fixed plus spherical-angular cost is charged once per actual switch.

Changing the first three items requires measured evidence and a new policy
version; they must not be silently reinterpreted.

## Current limitations

- Typed evidence covers 380–415, not the full 616.392-second Skiing source.
- The rejected 386-second onset demonstrates one false positive class, not a
  calibrated general onset detector.
- No real benchmark proves identity through occlusion, view handoff or an ERP
  seam. Geometry, faces and mouth motion must not manufacture identity.
- Group framing and reaction editing each pass only bounded cases; neither is
  a general director.
- SmolVLM2 500M and the 2.2B pairwise editorial adapter remain rejected.
- Flat post-warp stabilization is not the primary comfort solution, and source
  shake versus intentional motion still requires segment-aware treatment.
- The numeric planner emits decisions, not renderer commands. A separate
  validated adapter remains required before any production render.

## Active acceptance gate

Scale the same continuous acquisition contract to the full Skiing source, then
measure onset count before committing to semantic review volume. Preserve one
continuous hysteresis state; do not concatenate independently classified
windows. Only complete observed segment evidence may reach the renderer gate.

Before asking the owner to view a result, agent pre-review must establish that
the planned output differs materially, preserves image quality, and answers a
specific directing question. No new video is currently awaiting owner review.

## Verification

- `python3 -m unittest discover -s tests -q`: 498 tests pass.
- Typed packet/relevance/utility/continuity/planner integration: 53 tests pass.
- `python3 scripts/check_handoff.py`: passes.
- `git diff --check`: passes.

## Next action

Checkpoint and push the complete 380–415 replay and zero-candidate CLI/review
runner wiring. Then run a bounded-cost full-source onset-count acquisition;
do not render unless the resulting plan differs materially from an existing
validated baseline.
