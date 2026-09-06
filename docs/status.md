# Project status

Status: canonical full-source analysis proxy accepted

## Current conclusion

The repository has an executable offline analysis-to-render architecture for
monoscopic equirectangular input on the M4/16 GB reference machine. Full-source
motion onset and the active scene threshold both fail to recover the gradual
Skiing story states, so neither may remain the sole chapter signal. A canonical
lossless 960x480/10-fps FFV1 proxy now avoids paying the 5K VP9 decode cost for
each new low-cost signal. It preserves the declared analysis pixels exactly in
the bounded direct-source gate and has complete source/config/proxy lineage.

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

The exact artifact hashes are recorded in
`docs/experiments/skiing-continuity-transition-v1-2026-08-24.md`.

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

Exact commands, hashes, the initial duration-metadata failure and the corrected
result are in `docs/experiments/analysis-proxy-60s-protocol.md`.

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

## Active acceptance gate

Add a low-cost visual-state signal over the canonical proxy for gradual
activity/context changes. It must emit a separate path-free proposal contract,
use persistence/hysteresis, and grant no boundary by itself. Freeze a blind,
sparse review protocol before observing its Skiing proposals. Keep
frame-difference onset as motion-peak corroboration. Only complete observed
segment evidence may reach the renderer gate.

Before asking the owner to view a result, agent pre-review must establish that
the planned output differs materially, preserves image quality, and answers a
specific directing question. No new video is currently awaiting owner review.

## Verification

- `python3 -m unittest discover -s tests -q`: 512 tests pass before final
  documentation integration.
- Proxy-focused suite: 4 tests pass after the real Matroska-duration fix.
- Typed packet/relevance/utility/continuity/planner integration: 53 tests pass.
- `python3 scripts/check_handoff.py`: passes.
- `git diff --check`: passes.

## Next action

Checkpoint and push the canonical proxy contract and evidence. Then implement
the smallest deterministic coarse visual-state feature stream over that proxy;
do not change existing scene/onset schemas and do not render.
