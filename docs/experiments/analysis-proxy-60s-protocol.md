# Canonical analysis proxy gate

Status: 60-second equivalence and full-source acquisition passed on 2026-09-06

Use a declared 60-second source interval and run the atomic bundle CLI:

```sh
python3 scripts/build_analysis_proxy_bundle.py \
  SOURCE SOURCE_ID config/analysis-proxy-bundle-v1.json OUTPUT_BUNDLE \
  --start-seconds START --duration-seconds 60
```

`--start-seconds` and `--duration-seconds` are an all-or-nothing pair. The start
must be finite and nonnegative; duration must be finite and positive. Omitting
both creates a full-source proxy.

The source container may contain audio or other streams. The build selects only
`v:0`; the completed proxy container must contain exactly one video stream and
zero audio streams. Verify the manifest and proxy hashes, FFV1, 960x480
`yuv420p`, 10/1 CFR, SAR 1:1, and zero proxy start PTS. The manifest records the
requested interval as reduced rationals and maps proxy PTS to source time using:

```text
source_seconds = source_origin + proxy_pts * (1/10)
source_origin = source_video_first_pts * source_video_time_base + requested_start
```

Compare requested source timestamps with decoded proxy frames; maximum selection
error is 0.05 seconds. Record elapsed seconds and bytes only. Do not claim RSS or
swap without an independent measurement. A bounded proxy whose probed duration
differs from the request by more than one 10 fps frame fails validation. A bundle is renamed into place only
after exact manifest self-validation. Any encode or validation failure removes
its owned staging directory. Delete the external pixel-bearing proxy when the
experiment no longer needs it.

## Executed Skiing gate

The run used commit `b3f4a89`, macOS 26.5.2 (25F84), FFmpeg 8.1.1, and the
fanless M4 MacBook Air with 16 GB unified memory. RSS and swap were not
measured, so this result makes no memory or thermal claim. The source is the
checksummed `skiing_may_2019_360.webm` benchmark under the configured external
data root; no absolute path is part of the durable evidence.

The declared interval was 380–440 seconds. It includes the already reviewed
386.5-second high-motion non-chapter event and was selected before this run as
a codec, timestamp, and reuse gate—not as a story-threshold tuning sample.

The first real run rejected an implementation assumption: Matroska exposed
duration at the container level while the FFV1 stream duration was absent.
The runner failed before publication and removed its owned stage. The contract
now uses a validated stream duration when present and otherwise the validated
container duration; a regression test holds the latter case.

The corrected 60-second bundle contains 600 analysis frames, one video stream,
zero audio streams, and 85,943,004 bytes. Acquisition took 158.475 seconds.
Its proxy SHA-256 is
`bb56bf3298f3bb3f9b1cd34a48426860f906d0aad047edb7e51f25403e5c3b8c`.
Two proxy decodes produced identical frame digests. A direct source decode with
the identical filter chain also matched every decoded proxy frame; all three
framemd5 files had SHA-256
`87884c442c952d84f5b32d5434782f1018446b04de3569d5c07d1dd205aa0f63`.

The resulting full-source bundle contains 6,164 frames over 616.400 seconds
and 1,003,334,254 bytes. Acquisition took 249.783 seconds. Its proxy SHA-256 is
`493f68f31c8946cad785ffed49565276b0b96d897f5c5dcee548accaeaa30f20`;
the source SHA-256 remains
`d21e871c0428d22e8d71f5b4be24f7eb7a9ca925dcbcba9e3c912b74ae64827b`.
Two full-proxy decodes matched, with framemd5-file SHA-256
`b3c40a0a63e7acefc4d8931cfb5723ed2b1f3e54b0d81ef1b644e8c507a630ea`.
The path-free affine mapping records source origin as 7/1000 seconds.

The full proxy remains an external pixel-bearing analysis artifact. It is now
the canonical input for the next coarse visual-state experiment; it is not a
rendering input and grants no chapter or production authority.
