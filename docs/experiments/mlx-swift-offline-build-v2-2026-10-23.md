# MLXVLM offline build v2, 2026-10-23

Owner code `送 836` authorized one fresh T7 build attempt under plan SHA-256
`64336a2486209af06eb3bf8d525f5df0c43f5234c2af30c5ed42ecb6fc86e1df`.
Preflight found the v2 stage absent, v1 preserved, six source commits and
worktrees matching, three unique manifest replacements, and about 743 GiB
free on T7. The new stage at
`/Volumes/T7/aegis-360-items/build/mlx-swift-lm-stage-a-3.32.3-v2`
copies the pinned sources and fills the two gitlink paths only in that copy.
The three package dependencies point to local paths. Canonical source trees
and the Documents checkout stayed clean.

One `MLXVLM` target attempt used the outer network-denying sandbox and
SwiftPM `--disable-sandbox`, with package/scratch/cache/tmp/log paths under
the T7 stage, two jobs and a 30-minute timeout. It exited 1 after 11.3
seconds. The log `build.log` has SHA-256
`c7c574d4404b6c202859a7702cce84ac5757f7683eb38ba2819a889d49673942`.
SwiftPM passed manifest evaluation and entered build planning. It then
reported `unable to spawn process 'metal' (No such file or directory)` for
the `steel_attention.metal` kernel. The missing serialized diagnostics file
is a consequence of that error, not an independent compiler finding.

The selected developer directory is `/Library/Developer/CommandLineTools`.
Read-only `xcrun --find metal` returned no utility. Neither
`/Applications/Xcode.app` nor `/Applications/Xcode-beta.app` exists, and the
Command Line Tools path has no `usr/bin/metal`. This is a missing Metal
compiler/toolchain on the current host, not evidence of Swift/C++ source
compatibility or a completed `MLXVLM` build. The stage totals about 61 MiB,
with 10 MiB scratch and 88 KiB cache at readback. No `.air`, `.metallib`,
`.a`, or `.dylib` product was found by the bounded artifact search. No model
was loaded or run. The one-shot code is spent; no retry occurred.

Next identify an official, version-pinned Metal compiler route compatible
with this host. Installing it, changing the selected developer directory,
or rerunning the T7 build requires a new exact plan and authorization.
