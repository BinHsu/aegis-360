# Media pipeline

Status: Active POC design; acceleration choices are measurement-driven

## Configuration and storage

Machine-local `AEGIS_DATA_DIR` comes from CLI, process environment, or a
repo-local ignored `.env`; absence is an explicit setup error. Models, source
media, proxies, caches and outputs are stored beneath that root. Do not encode
the developer's volume path in source or traces. Detect a missing/disconnected
volume before expensive work and fail safely.

## Analysis pass

Validate streams/projection, then create or reuse a timestamp-preserving ERP
proxy. Analyze the proxy with bounded queues and staged models. Store compact
observations, tracks, evidence, candidates and plans. Avoid image-sequence
caches and full-resolution RGB/float tensors. Initial proxy resolution and
sampling rate are experiment parameters, not contracts.

## Preview and render

Render fixed, greedy and global low-resolution previews from the proxy.
Full-resolution rendering occurs only after selecting a plan: sequentially
decode source frames, reproject according to the path, preserve timestamp/audio
mapping unless benchmark policy mutes it, then encode 1920x1080 H.264 MP4.

FFmpeg `v360` is the correctness reference. VideoToolbox decode/encode, MPS,
Core ML or Metal may be used immediately when low-effort and reliable, but a
native implementation is commissioned only by a measured iteration,
throughput, memory or thermal bottleneck. Apple ecosystem lock-in is acceptable
for this POC; cross-platform behavior is not required.

## Memory and failure behavior

- All queues and caches have configured bounds.
- Normal peak RSS target is below 10 GB; record and investigate swap.
- Interrupted jobs leave atomic, identifiable partial artifacts that are safe
  to remove or resume; never overwrite source media.
- Cache keys include source hash/identity, relevant media metadata, model and
  weight checksum, configuration and schema version.
- Preserve color/timing metadata when supported; record any normalization or
  loss rather than silently claiming fidelity.

## Acceptance criteria

The three benchmark sources can be analyzed and previewed on the M4 Air 16 GB
without unbounded growth. A selected plan produces synchronized output, no
black projection gaps, a reproducible trace, and sustained metrics recorded by
the performance experiment.
