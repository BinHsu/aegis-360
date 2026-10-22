# MLXVLM offline build attempt, 2026-10-22

Owner code `送 635` authorized the one-shot T7 build plan with SHA-256
`d2bed5cbd8364ee61820e72617034525087f384d5c26fe374805f69c68e2a8d1`.
Immediately before execution, the isolated stage target was absent, all six
source commits and clean worktrees matched the plan, the three intended
manifest replacements were unique, and T7 had about 743 GiB free.

The stage at
`/Volumes/T7/aegis-360-items/build/mlx-swift-lm-stage-a-3.32.3-v1`
contains copies of the four Swift packages. The two pinned `mlx` and `mlx-c`
trees fill the gitlink paths in the copied `mlx-swift` only. The copied
`mlx-swift-lm` manifest points to local `mlx-swift` and `swift-syntax`; the
copied `mlx-swift` manifest points to local `swift-numerics`. Original T7
source worktrees and the Documents checkout stayed clean. No new package,
model or media source was downloaded.

One `MLXVLM` target build ran under an outer `sandbox-exec` policy allowing
default operations but denying network. SwiftPM used the stage's explicit
package, scratch, cache and `TMPDIR` paths, two jobs, `--skip-update`, and
`--disable-automatic-resolution`. The build exited 1 after 26.4 seconds.
The log at `build.log` has SHA-256
`1602eeb9d88ec704401e04c011967410568a993a7d2d33515c9678dcd22831cc`.
SwiftPM reported an invalid manifest because its inner `sandbox-exec`
returned `sandbox_apply: Operation not permitted` while compiling the
`mlx-swift-lm` package manifest. This is a nested sandbox failure before
source compilation; it does not establish source or host build compatibility.

The preserved stage totals about 50 MiB (packages about 50 MiB, scratch 12
KiB, cache 44 KiB, tmp 0 B at readback). No `.a`, `.dylib` or `.o` product
was found at the inspected stage depth, and the Documents checkout had no
`.build` directory. No model was loaded or run. The approved attempt is
spent; it must not be silently retried.

SwiftPM 6.4 advertises `--disable-sandbox` for its subprocesses. A later
attempt could combine that option with an outer network-denying policy, but
the resulting write/read scope and compiler-plugin behavior need an exact
reviewed plan before another T7 build. No such second attempt ran here.
