# Private sparse-story invocation boundary

Status: implementation design, no invocation authority

The retained probe session in `sparse_story_probe_denials.py` keeps one exact
batch candidate and its scratch root alive after a successful native probe. A
single private claim binds the 14 observed probe results and the hashes of the
backend manifest, runner policy and rendered enforcement-policy input. Its
private fixed-case methods now exercise the synthetic fixture through the
retained launcher. Closed no-owner, selected-read, scratch, and full-set read
and repository/protocol read cases can compare a frozen row before spawn;
read proofs close on rejection. Listener and outside sentinel cases can now
retain a prepared owner through freeze and execution, or clean its exact tree
on a changed row before spawn. This is a private one-case mechanism, not a
37-case coordinator. No general adapter or model invocation API is open.

## Required sequence

1. Revalidate the candidate, selected packet, launcher/runtime/model/prompt
   roots, policy bytes, uid/gid, and empty HOME/TMPDIR immediately before a
   claim is consumed.
2. Invoke the same retained native launcher and runtime through the same
   policy pipe and bundle directory descriptor used by the probe. Do not accept
   a caller-selected executable, policy, roots, request bytes or environment.
3. Transfer the length-prefixed policy and adapter stdin through separate
   bounded nonblocking pipes. Hold the launcher leader unreaped while checking
   its process group and terminating descendants. Confirm group absence before
   cleaning any owned side-effect tree.
4. Revalidate all retained input proofs and exact request bytes after process
   exit. Inspect scratch changes against an invocation-specific expected-write
   contract; preserve unexpected changes and report incomplete cleanup.
5. Close the candidate, then clean the exact owned scratch root. A failure at
   any earlier step cannot produce an invocation or aggregate receipt.

## Existing helper boundary

`capture_adapter_process` is a bounded pipe-capture utility for an injected
backend token. It calls `process.wait()` before the caller can verify group
absence and does not own the later scratch-file cleanup. Its fake-token tests
establish capture mechanics, not this native lifecycle. The private native
path must retain the leader until group teardown, as `_run_raw_probe` does.
The shared native transport now retains the leader for the fixed synthetic
cases. This is a transport design choice, not a new product decision or
permission to run a model.

## Prepared-case boundary

Listener ports and the outside-write sentinel path are created by their owned
resources. Their literal argv cannot be frozen before those resources exist.
An ordinary `frozen_row` argument cannot supply a valid row for a listener
whose port is allocated inside the case method. The claim can now retain one
listener or outside owner before freeze. The same owner supplies the literal
argv for a valid row and is used by the native invocation. A changed row
blocks spawn and removes only an unchanged owned tree. An unused prepared
owner closes with the session; a changed tree is preserved with a failure.

The next coordinator must prepare the complete schedule, freeze the 37 ordered
rows while their owners remain live, then execute each row through its retained
owner and candidate. Prepared owners may not be reconstructed from a frozen
path or port. The current one-case mechanism has not established aggregate
results, capability issuance or inference authority.

## Next discriminating checks

- A native synthetic no-write case must use the retained launcher/policy and
  exact six-variable environment, then leave the group absent and roots clean.
- A controlled live descendant must make incomplete cleanup observable and
  preserve owned trees if group absence cannot be proved.
- A changed selected leaf, policy, private directory or request must fail
  before spawn; a second claim cannot spawn.
- An expected scratch write must be removed only after exact identity and
  content checks. A replaced or unexpected file must remain for inspection.

No model or real-media acquisition follows from these checks.
