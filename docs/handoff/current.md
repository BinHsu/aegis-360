# Current handoff

Updated: 2026-09-06T15:35:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: b3f4a89
Remote status: `origin/main` at `b3f4a89` before this checkpoint
Working tree at checkpoint: canonical analysis-proxy implementation and evidence

## Objective

Build an offline 360-video auto-director for ordinary viewers on a fanless M4
MacBook Air with 16 GB unified memory. The next gate is a low-cost gradual
visual-state signal over the canonical proxy; it may propose sparse semantic
review but cannot grant a story boundary by itself.

## Last completed milestone

Commit `b3f4a89` records that full-source frame-difference onset and the active
scene-score threshold both fail to recover the known gradual Skiing chapters.
Do not retune either signal after seeing those results.

This checkpoint adds an atomic, checksummed, path-free reusable analysis proxy:
Matroska/FFV1, 960x480, yuv420p, 10 fps CFR, SAR 1:1, video-only, two FFmpeg
threads. The filter order is frozen as fps, scale, format, setsar, setpts.
Bounded start/duration arguments are exact rationals and must appear together.
The manifest records source, config and proxy hashes plus a rational affine
mapping from proxy PTS to the source timeline. It refuses overwrite, rechecks
the source hash, validates the completed manifest before same-filesystem rename,
and removes owned staging directories on encode or validation failure.

A real 380–440-second Skiing gate exposed and fixed one false assumption:
Matroska may omit stream duration while retaining container duration. The
corrected 60-second proxy matches a direct source decode frame for frame. The
full proxy then completed with 6,164 frames over 616.400 seconds.

## Repository state

- Expected branch and remote before checkpoint: `main` at `b3f4a89`.
- Expected dirty files are the proxy config, builder, CLI, tests, experiment
  record, documentation indexes, status and this handoff.
- External proxies and manifests remain untracked under the configured data
  root; no media or absolute path belongs in Git.

## Verified

- Focused proxy suite: 4 tests pass after the real-media fix.
- Full suite before documentation integration: 512 tests pass.
- 60-second proxy SHA:
  `bb56bf3298f3bb3f9b1cd34a48426860f906d0aad047edb7e51f25403e5c3b8c`.
- Direct and two proxy decodes share framemd5-file SHA:
  `87884c442c952d84f5b32d5434782f1018446b04de3569d5c07d1dd205aa0f63`.
- Full proxy SHA:
  `493f68f31c8946cad785ffed49565276b0b96d897f5c5dcee548accaeaa30f20`.
- Full proxy: 616.400 seconds, 6,164 frames, 1,003,334,254 bytes,
  249.783-second acquisition; repeat framemd5 digest matches.
- Source SHA remains
  `d21e871c0428d22e8d71f5b4be24f7eb7a9ca925dcbcba9e3c912b74ae64827b`.
- RSS, swap and thermals were not measured and are not claimed.

## Rejected

- Repeatedly decoding 5K VP9 independently for every low-cost signal.
- VideoToolbox H.264 as the canonical analysis artifact; it remains suitable
  only for previews because it is lossy and does not provide this pixel gate.
- Assuming Matroska always exposes duration at stream level.
- Frame-difference onset or active scene score as the sole chapter detector.
- Treating a proposal signal as an authorized story boundary.

## Pending

- Define a checksummed coarse visual-state feature stream over the full proxy.
- Introduce a separate path-free `chapter-proposal-candidates` contract with
  persistence, hysteresis, a frozen candidate cap, and no boundary authority.
- Freeze the blind Skiing review protocol before observing new proposals.
- Require two independent reviewers and precommitted negative/control packets.
- Only after observed semantic evidence may typed boundaries and the global
  planner be rebuilt. No video is awaiting owner review.

## Next commands

```sh
cd ~/Documents/aegis-360
python3 -m unittest discover -s tests -q
python3 scripts/check_handoff.py
git diff --check
git status --short
```

After checkpointing, implement the smallest deterministic gradual visual-state
feature stream over the canonical full proxy. Do not modify old scene/onset
schemas and do not render.

## External artifacts

Set `AEGIS_DATA_DIR` locally. Canonical proxy bundles are under
`outputs/analysis-proxies/skiing-t380-t440-ffv1-v1/` and
`outputs/analysis-proxies/skiing-full-ffv1-v1/`. Exact hashes and commands are
in `docs/experiments/analysis-proxy-60s-protocol.md`. Never commit these files.

## Active agents

No delegated work remains active. Proxy design, implementation, hardening and
review packets have returned; the main agent integrated and ran real media.

## Safety and claims

- Never commit media, frames, audio, model weights, identities or absolute
  local source paths.
- Analysis remains offline; downloads require explicit authority.
- Keep queues and memory bounded for 16 GB unified memory.
- Geometry, faces and mouth motion do not establish identity or speech.
- Git history is the archive; status and handoff contain current state only.
- Stop only for a real user decision, new authority or external dependency.
