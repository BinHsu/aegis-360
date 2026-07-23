# Perception projection comparison

Status: Planned

## Question

Does direct low-resolution ERP inference provide sufficient candidate recall
and track continuity, or are overlapping rectilinear viewports worth their
cost?

## Decision unlocked

Select the initial perception projection strategy and sampling configuration.

## Inputs

Short, manually reviewed excerpts from Bellpuig, Old Ghost Road and 360 Skiing,
including ordinary motion, seam crossings, small/distant riders and distorted
regions. Record source hashes and annotation procedure.

## Variants

- downscaled ERP;
- overlapping rectilinear viewports with documented coverage/overlap;
- optional ERP-proposal plus viewport refinement if neither is satisfactory.

Use identical model/weights and comparable sampling where possible.

## Metrics and acceptance criteria

Candidate/event recall, false/duplicate detections, identity switches, track
fragmentation, seam continuity, elapsed time, peak RSS, swap and cache size.
Choose the least costly variant that preserves candidates needed for directing
on all three excerpts. Define minimum reviewed-event recall and maximum
fragmentation before running; do not select solely by detector benchmark score.

## Run record

Commit, model/weight checksum/license, device placement, proxy dimensions/FPS,
hardware/OS, annotations, results, artifacts, limitations and conclusion: TBD.
No result has been observed.
