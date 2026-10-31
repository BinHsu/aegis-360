# Current handoff

Updated: 2026-10-31T21:34:00+08:00
Repository: aegis-360
Branch: main
Baseline commit: 9736867a98c24a845a6974adc29bf78505c8bcff
Remote status: `origin/main` matched baseline at last local verification; exact-SHA GitHub `validate` CI passed for baseline. This milestone is local and unpublished.
Working tree at checkpoint: milestone source, scripts and docs are expected edits; verify status before further work.

## Objective

Build an offline 360-video auto-director. Current bounded work diagnoses why the
first guided SmolVLM2 Stage A semantic candidate failed 3/6 known labels, then
prepares an independent successor gate. Global planning owns view choice (ADR
0010). Stage B cannot consume the rejected Stage A classes.

## Last completed milestone

The guided v3 result is published at `BinHsu/aegis-360@9736867` with exact-SHA
green `validate` CI. Two serial six-packet runs completed 12/12, were
byte-identical per packet, and got 3/6 labels right. A 2026-10-31 visual audit
localized the Old Ghost 205.6-second center error to observation, the Old Ghost
132.4-second error to a likely false artifact claim, and the Skiing 200-second
comparison to unresolved label/time scale. See
`docs/experiments/stage-a-guided-error-localization-2026-10-31.md`.

## Repository state

- The current source/docs milestone is local only. Confirm final changed files
  with `git status`; do not infer remote publication from a local commit.
- T7 holds all media, model weights, raw outputs, compiled binaries and build
  scratch. Only source, scripts and path-free aggregate evidence enter Git.
- The active SQLite task ledger is local and gitignored; no delegate is active.

## Verified

- Six diagnostic packets produced only two distinct parsed eleven-field
  objects. Altering artifact priority alone cannot recover the wrong classes.
- The visual center pair at Old Ghost 205.6 seconds changes from confined trail
  to bridge/river; the model called activity and setting unchanged.
- Frozen synthetic guided `static` and `palette_step` arms both passed
  operational gates but emitted identical 405-byte false-artifact JSON, even
  though `static` had six byte-identical images.
- Frozen unguided controls on the same inputs emitted different prose, and the
  static prose recognized no movement. They are not Stage A JSON candidates.
- First-token multimodal readouts had identical 1,023-token text prompt hashes
  but different 49,280-logit hashes. The image change affects model computation
  before guided decoding; top token ID was the same.
- The exact tokenizer/schema probe accepted complete `same`, `changed` and
  `artifact=present` objects through EOS. Alternate values are reachable;
  guided field-choice rankings remain unmeasured.

## Rejected and limitations

- Guided v3 is semantically rejected despite valid JSON and byte-level repeats.
  Do not feed its classes to the planner or tune accuracy on the exposed six.
- The Skiing 200-second human evidence described a coarse progression, not an
  exact center boundary. Its center class needs independent time-scale review.
- Synthetic static/palette failure does not prove the weights ignore images.
  Differing first logits do not prove changed enum values win under masking.
- No new independent real-media holdout, viewer preference or Stage B gate has
  passed. Sampled RSS is not unified-memory total.

## Pending

Inspect guided candidate rankings at field-choice tokens, then freeze an
independent, source-diverse center-event review pack excluding the six exposed
centers and their ±30-second neighborhoods. Human review must establish labels
before another model gate.
Cursor CLI is not logged in; the app account is visible, but an isolated
workspace and Grok 4.7 High route have not been verified. No payload was sent.
Remote publication of this local milestone requires separate authorization.

## Next commands

Validate the handoff, review the local diff, then use the design protocol to
prepare the independent review pack without running model inference on it:

```sh
cd ~/Documents/aegis-360
python3 scripts/check_handoff.py
git status --short --branch
python3 -m unittest discover -s tests -v
```

## External artifacts

The approved project data root is T7 `aegis-360-items`. Guided diagnostic
status and private media remain in its `build/sga4/` tree. Synthetic sensitivity,
unguided control, first-logit readouts and grammar build products remain in
separate T7 `build/` trees named by their scripts and experiment record.
The public-only Cursor review brief is under a private temporary directory;
no nonpublic input has been disclosed.

## Active agents

No delegated work or background job should remain when this checkpoint is
committed. Verify any live local build process before stopping or resuming it.

## Safety and claims

This is error localization, not a passing semantic candidate. A successful
local build or grammar acceptance proves only its bounded contract. The six
known-label packets are diagnostics and cannot serve as a new holdout. Git
history is the archive; this file describes only the latest state.
