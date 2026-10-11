# Debugging and review practice

This is a small repo-level adaptation of the debugging and code-review ideas in
[Superpowers](https://github.com/obra/superpowers). It is a procedure under
`AGENTS.md`, not a new authority to access data, delegate, publish, or change
the repository's acceptance gates. No Superpowers code or plugin is installed.

## Investigating a regression

1. Record the failing command, observed output, environment, and exact revision.
2. Reproduce the behavior or identify the missing observation. Trace the bad
   value or state across the relevant boundaries to its first divergence.
3. Compare the failing path with a nearby passing path and state one testable
   cause. Use the smallest discriminating probe or controlled mutation.
4. Add a regression check that fails on the old behavior, fix the cause, and
   run the focused check plus affected gates. Record skips and unrun scope.

For private sparse-story probes, inspect retained owner state, candidate
binding, pre-spawn order, process-group absence, and exact cleanup facts. A
passing test that never reaches the native launcher cannot establish its
runtime behavior.

## Independent review at a milestone

When an independent review would help, give the reviewer the bounded diff,
relevant contract, and explicit questions. Review contract compliance and
failure cases before style or maintainability. Check each reported issue
against the actual source and a reproducer or decisive code path before
accepting it. Record accepted findings, rejected findings and why, checks run,
and remaining limits in the milestone handoff.

External model review requires the task's specific data-transfer authority.
The reviewer receives only approved files; its answer is evidence to inspect,
not proof of correctness. Review does not replace the repository's tests,
handoff check, or exact-commit CI gate after an authorized push.
