# Apple Vision multi-clip tracking batch gate — 2026-07-23

## Purpose

The single-clip gate established that `VNTrackObjectRequest` can return a
continuous short track on one natural viewport. The batch runner makes the
same bounded experiment repeatable across several manually chosen clips.

## Manifest and command

`scripts/run_vision_tracking_batch_gate.py` accepts schema-version-1 JSON with
a non-empty `clips` array. Each clip supplies privacy-safe identifiers, a
local `inputVideo`, interval, sampling rate, viewport yaw, and normalized
initial box.

```sh
python3 scripts/run_vision_tracking_batch_gate.py \
  path/to/private-manifest.json \
  "$AEGIS_DATA_DIR/outputs/vision-tracking-batch/run-id"
```

The output directory must not exist. Each clip uses the stable single-clip
runner. `batch-report.json` holds per-clip numeric outcomes and aggregates;
raw evidence is kept under privacy-safe `clips/<clipId>/` directories.

## Privacy and interpretation

The report excludes source paths, filenames, commands, captured child output,
frames, and media metadata. Child failure names only its privacy-safe clip ID.

Weighted persistence is total tracked frames divided by total requested
frames. Maximum spherical step and seam crossings are diagnostics, not
acceptance thresholds. This gate does not establish subject identity, box
accuracy, seam handoff, recall, automatic initialization, or editorial value.

`tests/test_vision_tracking_batch_gate.sh` uses a deterministic fake of the
separately tested single-clip runner to verify aggregation, mixed outcomes,
overwrite refusal, and report privacy.
