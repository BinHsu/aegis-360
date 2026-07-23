# Privacy and offline runtime

Status: Active policy design

## Runtime boundary

Acquisition/setup may access the network only through an explicit user action.
Analysis, planning, preview and render run without network, accounts, login,
telemetry, update checks or silent downloads. Missing models/assets cause a
clear error referring to their manifest.

## Data lifecycle

- Source media and models remain under the user-configured external data root.
- Prefer video proxies and compact structured caches over extracted frames.
- Temporary frames and pixel buffers are bounded and released after use.
- Face/ReID embeddings, if introduced, are job-scoped, encrypted only if
  persisted for a demonstrated need, and deleted at job cleanup.
- Logs use job/asset IDs and relative artifact names; no absolute paths,
  transcripts, GPS/IMU payloads or image data.
- Cleanup is explicit, safe under interruption, and never deletes source media
  or unrecognized files.

## Verification

Offline behavior is tested with networking unavailable after all declared
assets are acquired. Record attempted connections and treat any runtime attempt
as failure. Review traces/logs using fixtures containing sentinel paths and
personal-like metadata to verify redaction.

## Acceptance criteria

All normal POC stages complete offline; assets are checksum-verified; no
implicit acquisition occurs; interrupted jobs expose and clean only owned
temporary artifacts; trace/log privacy tests find no forbidden fields.
