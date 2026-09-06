# Project status

Status: full-source motion-onset segmentation rejected as sole chapter signal

## Current conclusion

The repository has an executable offline analysis-to-render architecture for
monoscopic equirectangular input on the M4/16 GB reference machine. It now
includes typed continuous-onset segmentation and a persistent numeric global
planner. A 380–415 replay is production eligible and correctly retains the
existing cardinal-0 baseline. The complete 616.392-second replay then exposes
the limiting assumption: all seven motion onsets are non-story events, leaving
one segment whose three samples cannot support a whole-film view claim. The
full-source plan therefore abstains and remains non-production.

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
- Full-source acquisition emits 2,465 rows and seven onset candidates. Two
  independent reviews classify six `no_semantic_change` and one
  `capture_artifact`; zero story boundaries are authorized.
- The resulting single 616.392-second segment has 123-second uncovered ends
  and roughly 185-second gaps between its three samples. Relevance abstains;
  the final objective is zero and `production_eligible=false`.

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

- Motion onset has full-source evidence but does not recover gradual story
  chapters; it cannot remain the sole segmentation proposal source.
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

Add a low-cost chapter-proposal signal for gradual activity/context changes.
Keep frame-difference onset as motion-peak corroboration rather than the sole
boundary source. Evaluate proposals sparsely against the known lift → own
skiing → other-skiers sequence before rebuilding typed boundaries. Only
complete observed segment evidence may reach the renderer gate.

Before asking the owner to view a result, agent pre-review must establish that
the planned output differs materially, preserves image quality, and answers a
specific directing question. No new video is currently awaiting owner review.

## Verification

- `python3 -m unittest discover -s tests -q`: 508 tests pass.
- Typed packet/relevance/utility/continuity/planner integration: 53 tests pass.
- `python3 scripts/check_handoff.py`: passes.
- `git diff --check`: passes.

## Next action

Checkpoint and push the full-source negative result and transient onset review
runner. Then design the smallest offline chapter-proposal experiment that can
recover gradual context/activity changes without per-frame VLM inference.
