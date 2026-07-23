# FFmpeg v360 dynamic path

Status: Planned

## Question

Can the installed FFmpeg apply a timestamped yaw/pitch/FOV path correctly and
quickly enough for POC proxy previews and an occasional final render?

## Decision unlocked

Choose initial preview/final renderer and identify whether a Metal spike is
necessary for time-to-evidence.

## Inputs and variants

Use geometry fixtures plus short licensed benchmark excerpts. Compare static
poses, runtime/sendcmd path updates, continuous seam crossing, explicit cuts,
interpolation modes and CPU versus available VideoToolbox decode/encode where
compatible.

## Procedure

Capture exact commands/filter help/version; render paths with known timestamps;
inspect frame orientation, black borders, duration, frame count and A/V sync;
then measure cold and repeated proxy/full-resolution excerpts.

## Metrics and acceptance criteria

Record orientation/path error, duration/frame-count error, A/V offset, FPS,
wall time, peak RSS, swap, CPU/energy and command-file size. Accept for the POC
if semantics match geometry tests, output has no projection gaps or material
sync drift, proxy preview iteration is practical, and one final render can
complete within a documented budget on the reference machine. The budget must
be fixed before timed runs.

## Run record

Commit, hardware/OS, FFmpeg build, source hashes, commands, thermal state,
results, artifacts and conclusion: TBD. No result has been observed.
