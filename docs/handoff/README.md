# Handoff contract

`current.md` is the repository's vendor-neutral operational checkpoint. It
must let an unfamiliar Codex, Claude, Grok, human engineer, or other tool
continue without a prior transcript, private memory, session identifier, or
agent UI.

## Lifecycle

Update `current.md`:

- at every bounded milestone;
- before starting another large task or spawning new agents;
- after accepting or rejecting delegated work;
- before ending a work session;
- immediately when a usage, credit, quota, context, or service-limit warning
  appears.

The main agent normally owns `current.md`. Subagents return structured
completion packets instead of editing it concurrently.

Archive a meaningful completed checkpoint under `archive/` before replacing
it when historical operational detail would otherwise be lost. Accepted
architecture decisions still belong in ADRs, reproducible evidence in
`docs/experiments/`, and durable phase status in `docs/status.md`.

## Required content

The first metadata block and all headings in the template are required.

- `Updated` is an ISO 8601 timestamp with timezone.
- `Baseline commit` is an existing commit reachable from the current branch.
- `Remote status` and `Working tree at checkpoint` are explicit observations,
  not promises.
- `Verified` distinguishes passed checks from unexecuted or failed checks.
- `Pending` contains no claim of completion.
- `Next commands` contains exact commands runnable from the repository root.
- External artifacts use paths relative to the configured artifact root.
- Product-specific session IDs and instructions to inspect a prior chat are
  forbidden.

Run:

```sh
python3 scripts/check_handoff.py
```

CI also passes a base revision. If operationally significant files changed
without `docs/handoff/current.md`, validation fails.

## Subagent completion packet

Subagents return:

```text
status:
files_changed:
tests_run:
verified:
limitations:
unresolved:
recommended_next_action:
```

The main agent integrates or rejects that work and records the outcome in the
shared checkpoint.
