# Duration-ladder comparison protocol

Status: Protocol only; no benchmark result is claimed.

## Question

Does the auto-director remain watchable and useful as evaluation grows from a
quick camera-behavior check into a sustained directing and performance run?

## Contract

`benchmarks/duration-ladder.toml` is the machine-readable source of truth.
Run the nested duration ladder at a common start:

- 30 seconds: framing, obvious render defects, and abrupt camera motion.
- 60 seconds: subject dwell, switch timing, and viewing comfort.
- 180 seconds: continuity, repetition, event coverage, and accumulated drift.
- 300 seconds: long-view fatigue and sustained memory/throughput behavior.

For every enabled asset/duration pair, produce exactly these comparable
artifacts:

1. `fixed-forward`: the fixed camera baseline.
2. `auto-directed`: the selected auto-director configuration.
3. `debug-overlay`: the same auto-directed camera path with evidence, scores,
   and decisions visualized.

All three artifacts must use the same source, start timestamp, duration,
viewport/render settings, audio policy, and immutable configuration
identifier. The only permitted differences are the camera-path mode and debug
visualization. In particular, the debug artifact must not run a separate plan.

Use the same configuration at every duration. A tuning change starts a new
configuration series; do not silently tune after viewing a shorter rung and
present the longer rung as part of the old series. Because every rung begins at
the common start, the shorter result is a directly comparable prefix of the
longer result, subject only to deterministic encoding behavior.

## Asset eligibility

Eligibility is derived from `reported_duration_seconds` in
`benchmarks/manifest.toml`, not estimated from titles:

| Asset | Reported length | Enabled rungs |
|---|---:|---|
| Bellpuig | 282.381 s | 30, 60, 180 s |
| Old Ghost Road | 225.453 s | 30, 60, 180 s |
| Skiing May 2019 | 616.392 s | 30, 60, 180, 300 s |

Bellpuig continues to require the explicit projection override documented in
the benchmark manifest. It is a stress test, not spherical-error ground truth.

## Run record

Each run record must identify the asset id, source hash, start, duration,
configuration id, planner implementation, projection decision, output
settings, audio policy, and paths for all three artifacts. Performance runs
also follow `m4-air-sustained-performance.md`.

Validate the static contract before running local media:

```sh
python3 scripts/validate_duration_ladder.py
```

The validator performs no download and requires no benchmark media.
