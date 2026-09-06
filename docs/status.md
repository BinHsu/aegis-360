# Project status

Status: first gradual chapter policy rejected by blind control experiment

## Current conclusion

The repository has an executable offline analysis-to-render architecture for
monoscopic equirectangular input on the M4/16 GB reference machine. Full-source
motion onset and the active scene threshold both fail to recover the gradual
Skiing story states, so neither may remain the sole chapter signal. A canonical
lossless 960x480/10-fps FFV1 proxy now avoids paying the 5K VP9 decode cost for
each new low-cost signal. It preserves the declared analysis pixels exactly in
the bounded direct-source gate and has complete source/config/proxy lineage.
A deterministic 1-fps visual-state stream derives 616 path-free compact rows
from the full proxy in 22.93 seconds. Its values remained uninspected until the
persistent-state proposal policy and blind review protocol were frozen. The
policy then ran once, emitted two review-only proposals and was not retuned.
Blind review rejects both while independently detecting one control transition.

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
- The active 10 fps/320-pixel scene-score replay completes over the whole
  source and emits zero events above 0.25. It also fails to recover gradual
  chapters; the threshold is not retuned after observing the result.

## Canonical analysis proxy

- The closed config fixes Matroska/FFV1, 960x480, yuv420p, 10 fps CFR, SAR 1:1,
  video-only output, two threads and exact filter order.
- The atomic builder refuses overwrite, checks the source before and after,
  validates whole-container stream count, records rational timeline mapping,
  validates the exact manifest, and only then renames the bundle into place.
- The 380–440-second gate is 60.000 seconds and 85,943,004 bytes. Two proxy
  decodes and a direct-source decode match frame for frame.
- The full Skiing proxy is 616.400 seconds, 6,164 frames and 1,003,334,254
  bytes. Acquisition took 249.783 seconds; two decoded-frame digest runs match.
- The proxy contains external pixels and is never committed. It grants no
  semantic, story-boundary, camera-path or render authority.

## Visual-state and proposal freeze

- `aegis360.visual-state-features.v1` streams 96x48 RGB frames with a fixed
  16-frame history and emits luma, spatial, color, edge and five/15-second
  descriptors. It retains no decoded pixels.
- The real artifact contains 616 rows, is 859,874 bytes, and has SHA-256
  `81c92d89cc51190145e89fd5d02a95c5e480794fa22e0127dafd84b9391b2c91`.
  An independent repeat is byte-identical.
- A real run corrected the FFmpeg `fps=1` count oracle from ceil to frozen
  near-rounding semantics. The rejected attempt published no artifact.
- The proposal config compares complete half-open 20-sample states on either
  side of a 20-second guard, subtracts within-state dispersion, and requires
  `max(0.08, median + 3*MAD)`. It never backfills to six.
- Local maxima use a 10-second radius, earliest plateaus and 45-second greedy
  separation. Every peak retains an explainable rejection/emission audit.
- The blind protocol and numeric policy were fixed before any real feature
  value, peak or timestamp was inspected. A proposal grants review scope only.
- The one frozen execution emits review-only proposals at proxy seconds 46 and
  297. A qualified peak at 337 is suppressed by the 45-second separation rule.
- Deterministic unlabeled controls resolve to seconds 200, 140 and 460 without
  pixel, feature, label or hidden-key inspection.
- Two fresh-context reviewers agree on all five outcomes: both proposals are
  `no_semantic_change`; the second-200 control alone is `story_change` from a
  populated lift/station area to an open slope.
- The exact private/public projection and sanitized transient renderer expose
  no time, cardinal geometry, score, proof hash or proposal/control role.

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
- Proxy RSS, swap and thermal behavior were not measured; only elapsed time,
  bytes, metadata, hashes and decoded-pixel equivalence are established.
- Compact visual-state rows grow linearly at one row per second. Frame memory
  is bounded, but arbitrary-duration constant-memory JSON is not established.
- The absolute proposal score floor of 0.08 is a pre-data hypothesis, not a
  calibrated probability or accepted chapter threshold.
- The frozen persistent-state proposal policy misses the observed second-200
  change and emits two observed negatives. It is rejected as a chapter detector;
  this five-packet result is not a calibrated precision/recall estimate.
- Numeric audit shows RGB palette shifts dominate 46/297 while the station-to-
  slope change at 200 has weak coarse structure. The reciprocal 297/337 peaks
  are one A→B→A visual excursion, which separation does not model.
- The frozen structural contrast primary passes: chapter event 0008 scores
  0.15776835 versus within-chapter 0005 at 0.08512510. The report-only
  correlated 0018/0019 pair reverses, so only blind replication is permitted.
- Blind replication adds an independent reversal: the 205.6-second unanimous
  story change scores below the 132.4-second unanimous no-change packet.
  Viewpoint and spatial rearrangement remain confounds after cyclic alignment.

## Active acceptance gate

The structural blind replication is rejected. Both reviewers agree on all eight
packets and supply adequate 6:2 story/no-change classes, but minimum story score
0.04363508 is below maximum no-change score 0.06806761. This descriptor is not a
monotonic story-change ranker and grants no boundary, camera or render authority.

The model-neutral sparse story semantic successor protocol and synthetic
schema/binder implementation passed independent audits. Strict raw-byte binding,
closed operational failures and failure-bound abstention now have executable
coverage. The sanitized private-to-public projection also passes its synthetic
gate with complete-set binding and salted role-neutral ordering. The closed
synthetic media-tree gate now passes too: sanitized PNG leaves are input-derived,
published atomically without replacement, continuously descriptor-bound through
result publication and fail closed under mutation. No model or real media has
been acquired and neither Stage A nor Stage B has run, so this remains contract
evidence rather than semantic evidence.

The audited runner now has non-authoritative codecs, bounded capture and retained
asset proof, but no backend/coordinator or process-isolation/model-invocation claim.

Before asking the owner to view a result, agent pre-review must establish that
the planned output differs materially, preserves image quality, and answers a
specific directing question. No new video is currently awaiting owner review.

## Verification

- Full suite: 609 tests pass after retained asset-tree integration.
- Media-tree focused suite: 6 tests pass, including Darwin no-overwrite.
- `python3 scripts/check_handoff.py`: passes.
- `git diff --check`: passes.

## Next action

Implement coordinator-owned capability proofs; acquire no model or real media.
