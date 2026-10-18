# Stage A real-media input preflight, 2026-10-18

Status: local media-input gate only; no semantic model or Stage A outcome.

## Inputs and method

The frozen Old Ghost Road v5 proposal/control timeline and Skiing 10-fps
zero-event timeline were rebuilt by `scripts/build_stage_a_preflight_bundle.py`
from their upstream JSON and benchmark-manifest-bound source media. The local
runner compared every byte of the rebuilt fourteen files with the previously
published Stage A preflight bundle before decoding either source. The manifest
SHA-256 is `5b5cfa39fa0d1cb0600ccca2f8c029d8ad16f4449d35f4e018e8fffc5a98a465`;
the adapter-index SHA-256 is
`41fe1ee21e1c7ad0c3325842222826e61a5953dc35d39309d3c54cbe49f841bb`.

`run_stage_a_media_preflight.py` then rendered the 36 declared rows serially
with FFmpeg 8.1.1 on macOS 27.0.1/arm64. Each row uses its private exact
rational source time and four cardinal `v360` viewports, arranged as a 960x540
2x2 PNG. Each PNG was passed through the closed sanitizer and atomically
published with the exact index and a separate result peer under an ignored
local output root. Each source SHA-256 was checked before and after rendering.
The output root contains no source video, audio, model weight or raw prompt.

## Result

Two independent full render/publish runs produced the same 36-leaf media set,
bundle-tree SHA-256
`fd65c7a5436829fadfd78a89b64d361f59a8934a98c8d3f3022dce3cebe6c5b1`,
and result SHA-256
`c48862d316cbb5e3f05bc704d4eda5bcf7dd7d5269f0b9ca4db3be9962f6d80c`.
The second run supplied these as required prepublication expectations. A
changed expected hash is rejected before output creation in a focused test.
The first run's sealed bundle revalidated from disk with 36 files, directory
mode 0555 and result mode 0444. Three representative 2x2 images were visually
inspected: both source scenes contain distinct cardinal content, with no
obvious blank panels or major codec corruption. This is a spot check, not a
complete image-quality review.

The local bundles are under the gitignored `outputs/stage-a-media-preflight/`
directory. They are private transient input artifacts, not repository content.
The closed result grants only sanitized transient-media input authority.

## Limits and next gate

No model was invoked. A native adapter, full runtime asset proof and Stage A
smoke remain pending. The full portable test discovery on this host ran 944
tests with 97 skips and one unrelated OS-backend failure: macOS 27.0.1 has an
additional ARM64 fat slice in `/usr/bin/sandbox-exec`, while the frozen backend
parser accepts exactly one ARM64E subtype. The older native-host proof must be
reviewed for this OS before it can grant invocation authority. The media gate
does not depend on that proof.

The next external-media publication is a separate write to the configured
data volume. It needs an exact target/hash plan and owner send code. Source
pixels must remain outside Git and the local duplicates need an owner-approved
cleanup plan after a verified replacement exists.
