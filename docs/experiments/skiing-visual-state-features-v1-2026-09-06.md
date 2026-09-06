# Skiing visual-state features v1

Status: acquisition accepted; proposal values not inspected at freeze time

## Question

Can the canonical proxy support a deterministic, inexpensive, pixel-free
feature stream for gradual visual-state proposals without repeatedly decoding
the 5K VP9 source or granting semantic authority?

## Frozen acquisition

- Commit before this milestone: `26ee87f`.
- Input: canonical full Skiing analysis proxy.
- Proxy SHA-256:
  `493f68f31c8946cad785ffed49565276b0b96d897f5c5dcee548accaeaa30f20`.
- Source SHA-256:
  `d21e871c0428d22e8d71f5b4be24f7eb7a9ca925dcbcba9e3c912b74ae64827b`.
- Sampling: 1 fps, 96x48 RGB24, FFmpeg area scaling, two decode threads.
- Per-sample features: global luma mean/standard deviation, 4x2 spatial
  luma, four-bin per-channel RGB histograms, four-neighbour edge strength,
  and five/15-second descriptors.
- Frame memory: current frame plus a fixed 16-frame history.
- Output rows contain no paths, pixels, audio, identity, semantic labels,
  proposals, boundaries, camera commands or renderer commands.

The environment is macOS 26.5.2 (25F84), FFmpeg 8.1.1, and the fanless M4
MacBook Air with 16 GB unified memory. Peak RSS, swap and thermals were not
measured and are not claimed.

## Real run and correction

The first real run predicted 617 rows from a 616.400-second proxy using
`ceil(duration)`. FFmpeg 8.1.1 `fps=1` emitted 616 rows under its default near
rounding, so the closed count gate rejected the artifact and published no
output. The rule is now frozen as
`floor(proxy_duration_seconds * 1fps + 0.5)`, with 16.4→16 and 16.6→17
regressions.

The corrected output contains 616 rows in 859,874 bytes. Its SHA-256 is
`81c92d89cc51190145e89fd5d02a95c5e480794fa22e0127dafd84b9391b2c91`.
A second acquisition took 22.93 seconds wall time (44.17 user, 0.61 system)
and produced an exactly identical file. The owned repeat artifact was deleted.

At the proposal-policy freeze point, only schema, hashes, row count, endpoint
indices, privacy and authority were inspected. No feature value, peak or
timestamp was printed or used to choose the proposal policy.

## Decision

Accept `aegis360.visual-state-features.v1` as low-cost acquisition evidence for
the frozen chapter-proposal experiment. It is not a chapter detector. The
single-JSON artifact accumulates one compact row per second; that is bounded
and small for this 616-second benchmark but is not a constant-memory claim for
arbitrary-duration media.

The next run must use the separately frozen proposal config and blind protocol
without threshold changes. Any proposal remains review-only until independent
semantic evidence passes.
