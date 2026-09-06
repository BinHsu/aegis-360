# Sparse story semantic successor v1

Status: protocol frozen; synthetic schema/binder, projection and media-tree gates implemented; no model or real media acquired

## Synthetic implementation checkpoint

`aegis360.sparse_story_semantics` implements the exact closed raw observation,
ordered binder, strict stdout-byte parsing, operational-failure precedence and
failure-bound canonical abstention. Its public success path computes the raw
output hash from strict-parsed bytes; its failure path rebuilds the artifact
from captured bytes and operational flags before binding it. Opaque packet IDs
are restricted to `packet-[0-9a-f]{20}`. Independent implementation audit passed
after raw-hash and failure-state bypasses found in earlier drafts were closed.
Eight focused tests and the complete 568-test suite pass. This checkpoint uses
synthetic JSON only and adds no semantic, model, media or performance evidence.

`aegis360.sparse_story_projection` now implements the subsequent pure-JSON
projection gate: exact private structure and canonical hashes, complete 1/6/24
packet-set binding, domain-separated salted IDs and presentation order, closed
anonymous projections and exact rebuild. Four focused tests plus the complete
572-test suite pass after independent audit caught and closed boolean row-number
acceptance and same-packet ID/order HMAC collision. It does not yet validate a
media tree or execution isolation.

`aegis360.sparse_story_media_tree` implements the closed synthetic PNG and
published-tree gate below. It validates and deterministically strips PNGs,
publishes an exact descriptor-validated read-only tree through Darwin's atomic
no-replace rename, retains the original open snapshot through result publication,
and proves every published leaf from the canonical index and original payloads.
Six focused tests and the complete 578-test suite pass. Independent causal and
vertical audits passed after closing snapshot-reopen, self-consistent forged-tree,
mutation-cleanup and result-mode bypasses. This grants only sanitized transient
media-input authority; it invokes neither a renderer nor a model.

The isolated adapter-runner protocol is now frozen after independent causal and
vertical audits. Its capability-test-first backend, exact asset/request/receipt/
aggregate schemas and synthetic case matrix are design authority only; no runner
production isolation PASS exists yet. Non-authoritative structural codecs and a
descriptor-bound, selector-driven capture primitive now pass 22 focused tests and
independent trust audit. Every authority-bearing derivation still fails closed;
the production backend, coordinator and publisher remain absent. The retained
asset-tree proof now independently derives a precommitted manifest through bounded
descriptor-relative traversal and passes 9 focused tests plus causal/vertical audit.

## Question and claim boundary

Can one bounded semantic observation per cheap-signal event distinguish a
persistent activity or setting change from viewpoint, foreground and capture
nuisances without per-frame VLM inference? The first gate establishes only
model/schema feasibility on known diagnostic packets. A later source-diverse
blind gate may establish held-out event-classification and proposal-recall
evidence. Neither gate grants an exact boundary, chapter map, camera choice,
temporal reorder or render authority.

The rejected RGB and grayscale structural policies remain negative evidence.
Their scores must not become inputs, thresholds, candidate ranks or labels.

## Ownership

- Cheap signals union scene change, motion onset, audio novelty/reaction or
  speech activity, detector/group deltas, track lifecycle and view availability.
  They schedule high-recall review scope only. Magnitudes cannot label, rank
  narrative importance or suppress a distinct event after local deduplication.
- The existing durable lineage packet owns its exact source interval, anchors,
  four-view coverage and private machine evidence. A new exact adapter-visible
  projection exposes only opaque packet ID, chronological row roles, safe media
  refs and anonymous view slots. It removes source/event/time/position, signal
  type/magnitude, expected class, geometry and edit request. The runner must
  prove this projection from the private packet before invoking an adapter.
- A replaceable local adapter emits only the closed observations below or
  abstains. It cannot emit timestamps, identities, confidence, prose, geometry,
  chapter labels, narrative function, candidate views or edit commands.
- A new successor evidence schema and deterministic binder derive one
  conservative event class. Only the provenance, closed-schema, abstention and
  authority patterns of `scene_story_semantics.v1` are reused; that schema
  itself is incompatible because it requires forbidden chapter and narrative
  labels. Typed boundary,
  complete chapter map, global planner and renderer remain later authorities.

## Closed observation contract

Every packet has no more than six chronological four-cardinal composites. The
raw adapter output contains exactly these fields:

| Field | Closed values |
| --- | --- |
| `status` | `observed`, `abstain` |
| `early_state_coherence` | `observed`, `not_observed`, `unclear` |
| `late_state_coherence` | `observed`, `not_observed`, `unclear` |
| `activity_relation` | `same`, `changed`, `unclear` |
| `setting_relation` | `same`, `changed`, `unclear` |
| `anonymous_participant_configuration` | `same`, `changed`, `unclear` |
| `transition_support` | `supports`, `contradicts`, `insufficient` |
| `viewpoint_change` | `present`, `absent`, `unclear` |
| `foreground_rearrangement` | `present`, `absent`, `unclear` |
| `exposure_or_palette_change` | `present`, `absent`, `unclear` |
| `capture_or_projection_artifact` | `present`, `absent`, `unclear` |

Participant configuration describes anonymous visible composition only; it
cannot assert correspondence or identity across rows.

Raw `status=abstain` requires every relation/coherence/nuisance field to be
`unclear` and transition support to be `insufficient`. The binder preserves and
hash-binds every valid raw observation unchanged, then emits a separate closed
`event_class` using this ordered truth table; every unlisted observed
combination derives `event_class=abstain` without rewriting the raw fields:

1. `capture_artifact`: status observed and capture/projection artifact present.
2. `story_change`: status observed; both states coherent; activity or setting
   changed; transition supports; and viewpoint, foreground, exposure/palette
   and capture/projection nuisances are all absent.
3. `no_semantic_change`: status observed; both states coherent; activity and
   setting both same; capture and exposure/palette nuisances absent; and either
   participant configuration is same, or it is changed while viewpoint or
   foreground rearrangement is present.
4. `abstain`: any valid observation not matched above.

A malformed, incomplete or forbidden raw model output is never accepted or
silently stripped. The runner first records a closed operational-failure
artifact whose `reason` is exactly one of `malformed_json`, `schema_violation`,
`forbidden_field`, `missing_anchor` or `invocation_failure`. It contains packet
ID, private-packet SHA-256, adapter-projection SHA-256, model-asset SHA-256,
`prompt_schema_bundle_sha256` for one canonical artifact containing both the
prompt and schema, `raw_output_present` and `raw_output_sha256`. Assign exactly
one reason using first-match precedence: pre-invocation `missing_anchor`, then
`invocation_failure`, `malformed_json`, `forbidden_field`, and finally
`schema_violation`. The final
hash is SHA-256 of the exact captured stdout bytes; when no bytes exist it is
the SHA-256 of the empty byte string and `raw_output_present=false`. The artifact
stores only closed fields and digests, never offending bytes, stderr or free
text. The binder constructs the canonical all-unclear/insufficient raw
abstention and binds both it and `event_class=abstain` to the failure-artifact
SHA-256. Participant configuration alone never manufactures a story change or
chapter.

## Sanitized projection synthetic gate

Before any media or model run, implement a pure-JSON projection from a complete
set of structurally validated private packets to a role-neutral public index.
This gate proves exact sanitization only. A prior, separate lineage gate must
prove each private packet from the frozen execution manifest, timeline and grid;
changing a private hash or time creates a different input and is outside the
projection gate's authority. The execution manifest freezes only pre-projection
selection identities and order, never opaque IDs or a public-index hash, so its
hash cannot depend circularly on the projection.

The private packet schema is `aegis360.sparse-story-private-packet.v1` with
exact top-level fields `schema_version`, `source_id`, `selection`, `inputs`,
`center_source_time`, `rows`, `privacy` and `authority`. `selection` contains
only `role` (`proposal` or `control`), `original_event_id` (string for proposal,
null for control) and `original_signal_ids` (a non-empty unique string list for
proposal, empty for control). `inputs` contains exactly the four SHA-256 values
`execution_manifest_sha256`, `source_sha256`, `event_timeline_sha256` and
`context_view_grid_sha256`. Center and row source times are reduced positive-
denominator rational `{numerator, denominator}` objects. `rows` has exactly the
six numbered roles below in order; each row contains only `row_number`,
`row_role`, `absolute_source_time` and `cardinal_views`. `cardinal_views` is the
same ordered four-item list on every row; each item contains exact private
`candidate_id`, `yaw_degrees`, `pitch_degrees` and
`horizontal_fov_degrees`. Rows equal center plus the exact rational offsets
`-15`, `-3`, `-1/4`, `+1/4`, `+3`, `+15` seconds without clamp or deduplication;
negative row times are invalid. Proposal and control packets have the same
shape; controls use null event ID and an empty signal list rather than inventing
a timeline event.

`source_id`, every non-null original event/signal ID and every candidate ID are
nonempty strings matching `^[A-Za-z0-9._:+/-]+$`. Candidate IDs are unique and
the exact same ordered four IDs occur on every row. Booleans are not numbers;
geometry values are finite integers or floats with yaw in `[-180, 180)`, pitch
in `[-90, 90]` and horizontal FOV in `(0, 180]`. Original signal IDs are unique.
Every rational is reduced, its denominator is positive, and center/row source
times are nonnegative.

Private `privacy` is exactly `contains_source_path=false`,
`contains_pixels=false`, `contains_audio=false`,
`contains_expected_class=false`, `contains_reviewer_result=false`. Private
`authority` is exactly `lineage_input=true`, `semantic_observation=false`,
`exact_boundary=false`, `chapter_map=false`, `camera=false`, `reorder=false`,
`render=false`. The private packet SHA-256 is over sorted, compact,
ASCII-escaped JSON encoded as UTF-8 with no trailing newline.

The coordinator accepts an exact 64-character lowercase hexadecimal secret
salt. The HMAC key is exactly the 32 bytes obtained by decoding that hex, not
the 64 ASCII characters. For each private packet it computes two full lowercase-
hex HMAC-SHA256 values over exact UTF-8 messages with no newline:
`id|successor-packet-v1|execution_manifest_sha256|private_packet_sha256` and
`order|successor-packet-v1|execution_manifest_sha256|private_packet_sha256`.
It exposes only `packet-` plus the first 20 ID-HMAC hex characters, sorts the
complete packet set by full order HMAC with full ID HMAC as tie-break, and
exposes only the resulting one-based presentation ordinal. Salt and full HMACs
remain private. The set-level builder rejects any duplicate private-packet hash,
full HMAC or truncated packet ID. Plain hashes of enumerable event/time values
are forbidden.

The adapter-visible projection is exactly:

```text
schema_version: aegis360.sparse-story-adapter-index.v1
packet_count: exact length of the complete private set
packets:
  presentation_ordinal: 1..packet_count
  projection:
    schema_version: aegis360.sparse-story-adapter-projection.v1
    packet_id: packet-[0-9a-f]{20}
    rows: exactly six rows
      row_number: 1..6
      row_role: early_far, early_near, transition_before, transition_after,
                late_near, late_far
      media_ref: media/<packet_id>/row-01.png ... row-06.png
      views: exactly [view-1, view-2, view-3, view-4]
```

Every projection's `privacy` is exactly these false-valued keys:
`contains_source_id`, `contains_event_id`, `contains_signal`,
`contains_source_time`, `contains_position`,
`contains_proposal_control_role`, `contains_lineage_hash`,
`contains_signal_evidence`, `contains_score_or_confidence`,
`contains_expected_class`, `contains_identity`,
`contains_real_candidate_id`, `contains_geometry`, `contains_chapter_label`,
`contains_narrative_function`, `contains_prose`, `contains_edit_request`.
Every projection's `authority` is exactly `semantic_observation_input=true`,
`exact_boundary=false`, `chapter_map=false`, `camera=false`, `reorder=false`,
`render=false`. The public index adds no other top-level fields. Each projection
SHA-256 used by the evidence binder is over that projection's sorted, compact,
ASCII-escaped JSON encoded as UTF-8 with no trailing newline.

The projection builder must also receive the exact ordered private-packet
SHA-256 list already emitted by the prior lineage gate. It is nonempty and has
exactly 1 item for the Stage A smoke, 6 for either complete Stage A run, or 24
for Stage B. The supplied private packet sequence must match that list exactly,
and every packet must contain the same `execution_manifest_sha256`; omission,
addition, duplication or reorder fails. The entire public index uses the same
sorted compact ASCII-escaped UTF-8 JSON with no trailing newline; its SHA-256 is
computed externally over those bytes and never embedded in the index.

Rows retain chronology but expose no timestamp or offset. Views retain stable
within-row slots but expose no candidate identity or direction. Media refs are
relative, path-normalized, contain only the opaque packet ID and fixed row
number, and permit no symlink or extra file at the later media-tree gate. Exact
closed projection equality is the sole leakage rule: no independent substring
or private-value blacklist is used, because numbers and strings can coincide
innocently. The set-level validator structurally validates every private packet,
recomputes its canonical hash, both HMACs, order, IDs and complete public index,
then requires exact equality.

The synthetic gate passes only when exact rebuild is byte-stable; mutations,
row reorder/drop/add, unsafe refs, salt/hash mismatch, extra public fields and
opaque-ID collisions all fail closed. This gate grants projection
and adapter-input authority only. PNG sanitization, closed media-tree proof,
minimal process environment, repository/filesystem isolation, network denial,
stdout capture and model invocation remain separate runner gates.

## Closed media-tree synthetic gate

Before a real renderer or adapter runs, build a temporary bundle only from a
validated adapter index and caller-supplied synthetic PNG bytes. The bundle root
has `adapter-index.json` plus every unique declared `media_ref` as its only file
leaves. Its exact directory set is the root plus only the unique proper ancestors
required by those leaves: `media/` and each declared opaque packet directory.
Empty/extra directories, symlinks and every other node type are forbidden.
`adapter-index.json` is the exact canonical index bytes and matches its supplied
SHA-256. Every ref has exactly one caller-supplied immutable `bytes` payload;
missing, duplicate and extra refs fail. The builder records every input digest
before sanitization, never edits caller buffers/files in place, then requires
the same ordered ref/digest list after completion.

Each row image is exactly 960x540, PNG bit depth 8, truecolor RGB or RGBA,
non-interlaced, with standard compression and filter methods. Every chunk type
is four ASCII letters with its reserved third letter uppercase. The sanitizer
verifies signature, chunk length/order/CRC, one IHDR, one or more consecutive
IDATs, one terminal IEND and no trailing bytes. It rejects every other critical
chunk, including PLTE; ancillary chunks are discarded. Concatenated original
IDAT payloads must form exactly one zlib stream reaching EOF with no unused data,
unconsumed tail or second stream. It expands to exactly
`height * (1 + width * bytes_per_pixel)` bytes and has filter byte 0–4 at each
scanline boundary. Output contains the original IHDR, one IDAT whose payload is
the byte-for-byte concatenation of all original IDAT payloads, and IEND, with
recomputed CRCs. Malformed, mismatched or undecodable PNG fails closed.

Publication uses a same-filesystem sibling staging directory created mode 0700
under an explicit owner-only umask; it is the only writer. Directories start
0700 and leaves 0600 through no-follow, exclusive descriptor-relative opens.
Each completed leaf is fsynced, chmod 0444 and fsynced again. Required
directories are sealed bottom-up to 0555 and fsynced, followed by the staging
root and destination parent. The one publication operation is macOS
`renamex_np(..., RENAME_EXCL)` or a proven equivalent no-replace syscall;
unsupported platforms fail instead of falling back to exists-then-rename.
After a successful exclusive rename, the destination parent is fsynced again
before any success or result is reported.

Validation opens the root and every path component descriptor-relatively with
no-follow semantics, compares actual names/types to the exact file/directory
sets, and retains descriptors through the tree decision. Every leaf `fstat` is
regular with link count one; device, inode, size and nanosecond mtime remain
stable around hashing. The retained descriptors produce the frozen digest,
remain valid across same-filesystem rename, and reproduce it afterward; the
destination path must resolve to the recorded root device/inode. A post-publish
mismatch removes the destination only if that root identity still matches the
owned published root. A pre-existing/replacement target is never removed, and
pre-publication failure removes only the owned staging directory.

The canonical tree digest is SHA-256 over UTF-8 lines
`<lowercase-hex-SHA256(file bytes)><two ASCII spaces><relative_posix_path><LF>`
for every expected file
in bytewise path order, including `adapter-index.json`; the digest is external
and not embedded, and the last line also ends in LF.

The closed result outside the bundle has schema
`aegis360.sparse-story-sanitized-media-result.v1` and exactly the top-level keys
`schema_version`, `inputs`, `outputs`, `privacy`, `authority`. `inputs` contains
exactly lowercase-hex `adapter_index_sha256`, string `sanitizer_contract_id`
equal to `sparse-story-png-rgb-rgba-960x540-v1`, and `input_payloads`.
`input_payloads` is a unique list exactly matching all index refs, sorted by
bytewise `media_ref`, whose rows contain only safe string `media_ref` and its
lowercase-hex input-bytes `sha256`. `outputs` contains only integer
`media_file_count`, integer `total_file_count` and lowercase-hex
`bundle_tree_sha256`; booleans are not integers, media count equals the unique
ref count, and total count equals media count plus `adapter-index.json`.
`privacy` is exactly `contains_source_path=false`, `contains_pixels=false`,
`contains_audio=false`, `contains_identity=false`,
`contains_source_time=false`, `contains_free_text=false`. `authority` is exactly
`sanitized_transient_media_input=true`, `semantic_observation=false`,
`exact_boundary=false`, `chapter_map=false`, `camera=false`, `reorder=false`,
`render=false`, `model_invocation=false`. It uses sorted
compact ASCII-escaped UTF-8 JSON without newline, is hashed externally, and must
exact-rebuild from the index, original bytes and published tree.

The bundle publisher returns canonical result bytes only after post-rename tree
verification; it does not publish the external result. A separate caller-owned
writer persists those bytes using sibling staging, file fsync, exclusive no-
replace rename and parent fsync, then revalidates exact bytes/hash. Bundle and
result are explicitly not one atomic transaction. The coordinator treats the
gate incomplete until result persistence revalidates; if it fails, it removes
the bundle only while the recorded root device/inode still proves ownership.

The synthetic gate must prove deterministic sanitized bytes/tree digest; exact
scope; rejection of extra/missing/reordered refs, path traversal, symlink and
hardlink entries; metadata/unknown-critical/truncated/CRC/zlib/scanline/filter/
dimension failures; no overwrite including a destination created immediately
before publication; pre/post tree identity; bounded owned cleanup; exact result
rebuild; and source-byte immutability.
It grants sanitized transient-media input authority only. Real FFmpeg rendering,
source-time seeking, process environment, repository/filesystem isolation,
network denial, adapter stdout and post-invocation deletion remain later gates.

## Isolated adapter-runner synthetic gate

This gate is separate from media publication and model quality. One coordinator
call owns one validated opaque packet and starts exactly one fresh child process
group. There is no retry, repair prompt, fallback backend, reused conversation or
worker reuse between packets. `missing_anchor` is unreachable here: the runner
accepts only a complete one-packet projection and six-file media tree; missing
media is invalid upstream proof, not a caller flag. Invalid lineage,
index, tree, executable/runtime/model/prompt manifest or isolation policy is
`invalid`, emits no semantic evidence and starts zero children.

Before spawn, bind the private packet and canonical hash, exact adapter projection
and hash, validated adapter index, retained input-derived media-tree proof, exact
six packet refs, executable/runtime manifest, closed multi-file model manifest,
prompt/schema bundle and runner policy. Every manifest uses a canonical sorted
compact JSON representation and binds each regular no-follow file by relative
path, mode, size and SHA-256 plus a canonical tree digest. Absolute paths remain
private except the transient allowlisted model/prompt root handles in stdin; no
absolute path enters stdout-derived or durable results.

Runner policy v1 fixes a 120-second monotonic wall timeout, two-second termination
grace, 65,536-byte stdout ceiling and 65,536-byte stderr ceiling; each pipe retains
one extra byte solely to prove overflow. These values cannot be tuned after model
output is seen. The child receives one canonical request on stdin followed by EOF.
It contains only the opaque packet ID, anonymous projection, bundle-relative
handles for the six sanitized media files and transient absolute handles for the
prompt/schema and model roots. It contains no source,
time, event/signal/proposal role, geometry, expected class, reviewer material,
repository/protocol/history, prior output, salt, HMAC, private hash or destination.

Invoke an absolute, regular, non-symlink executable directly with no shell, in a
new process session with the sealed one-packet bundle as cwd and umask 077. Close every
non-stdio descriptor and pass none explicitly. Build a fresh environment without
copying the parent: exactly `LANG=C`, `LC_ALL=C`, `TZ=UTC`, `NO_COLOR=1`, private
`HOME` and `TMPDIR`; v1 permits no additional variables. `PATH`, proxy,
credential, cloud, SSH, telemetry, `DYLD_*`, `PYTHON*` and repository/data
variables are absent. Another variable requires a new frozen policy version.

An isolation backend is mandatory and must capability-test its installed policy
before every execution batch. Default deny must demonstrably allow only exact
system/runtime/model/prompt/sanitized inputs for read and the private scratch for
write, while denying the frozen IPv4, IPv6 and filesystem-AF_UNIX connect
operations, unauthorized process execution, repository
and protocol reads, other packet/result reads and every outside write. Probes use
actual operations and sentinels, not command inspection. A skipped probe, policy
installation error, unexpected allow or unavailable backend is `invalid` with
zero adapter invocations. Presence of `/usr/bin/sandbox-exec`, a clean environment,
temporary cwd or `shell=false` is not isolation evidence and never authorizes an
unsandboxed fallback. A finite probe proves only the frozen matrix plus inspection
of its default-deny policy, not universal confinement. The deprecated Seatbelt CLI remains only a candidate until
this exact capability gate passes on the execution host.

The 2026-09-06 backend-feasibility audit fixes four ambiguities without granting
backend authority. `compiled_policy_sha256` is a legacy field name for the SHA-256
of the exact canonical enforcement-policy input bytes installed for the batch;
it does not claim access to opaque kernel-compiled policy. A backend manifest must
separately bind the backend executable, launcher, OS build and the canonical rule
for those bytes. The finite system-read base is an explicit, sorted set of
OS-owned allowlisted literal/subpath rules in that manifest, not an `allow default`
or an unbounded `system` category. Every non-system retained root remains an exact
batch path. This scopes policy access and does not claim content identity or
immutability for system files. The single initial direct exec of the bound runtime entrypoint is the
bootstrap exception; `denied_process_exec` means an attempted exec of the separate
coordinator-owned forbidden executable sentinel returns EACCES or EPERM and causes
no sentinel side effect. Re-exec of the exact allowlisted runtime image is not
claimed denied, remains under the same inherited confinement, and cannot create a
child because fork is independently denied. `denied_unix_socket` means connect to
a live coordinator-owned filesystem AF_UNIX listener returns EACCES or EPERM and
the listener accepts zero connections. `denied_outside_write` requires all of:
failed create in an existing forbidden directory, failed overwrite/truncate of an
existing sentinel, failed rename of a coordinator-owned scratch source sentinel
into that directory and failed unlink of the existing sentinel. Each requires
EACCES or EPERM; the scratch rename source and forbidden destination retain exact
pre/post name, type, device/inode, mode, size and content, and both parent name maps
remain unchanged. These definitions narrow
the receipt to observable operations; they do not claim universal syscall denial.

The next Seatbelt spike is feasibility-only. It may retain raw operation names,
errno values, exact sentinel pre/post facts, host/tool identity and candidate
profile bytes, but it must not construct a backend manifest, runner policy,
single-use token, capability receipt, run receipt/result, aggregate, or any
protocol `pass`/`reject` outcome. Its only terminal vocabulary is `feasible` or
`not_feasible`, neither of which grants authority. Backend schema and native
Mach-O retained-proof enforcement remain later gates even if every primitive is
feasible.

The synthetic Seatbelt spike ran in the host context on macOS 26.5.2
(`25F84`, arm64). The initial finite system-read candidate aborted in dyld before
`main`. A single-variable retry adding exact `file-read-metadata` for literal
`/tmp` removed that denial but retained an exact `file-read-data /` denial and
the same abort; its path-bound candidate policy SHA-256 was
`f41c62c20393c160c6a9a0a59dfec8a7794fbeae85fe3967fd9141838babd2d0`.
The next candidate added exact `file-read-data` for literal `/`, never
a root or temporary subpath. Its path-bound policy SHA-256 was
`5f2a954eed7c0b9e3911c4e1495437f365d0d089ff2b677d3329d8deb9b1098f` and the
harness classified it `feasible`: exact allowed reads and scratch write
succeeded; every frozen forbidden read, compound outside write, fork,
forbidden-exec and connect operation returned EPERM; all three sockets were
created; all listeners accepted zero connections; exact sentinels, private
directories and process-group state passed their pre/post checks; exit was zero
with empty stderr. Temporary resolved paths and candidate bytes were destroyed
by design, so these hashes identify those executions but are not independently
reconstructible manifests. This is host-specific primitive feasibility only and
creates no capability or production-backend authority.
One least-privilege follow-up removed the broad, matrix-unneeded `sysctl-read`
allowance and retained the same complete `feasible` result. Its path-bound policy
SHA-256 was `1a545dcff8764090d0d8586c6c681a7fb90f2613aad301f04f17d95b20933128`;
renderer v1 therefore contains no sysctl allowance.
After the exact backend shape and sole renderer were frozen, the harness moved
the probe beneath a disjoint runtime root and consumed those policy bytes
directly. The host matrix remained fully `feasible`; its path-bound canonical
policy SHA-256 was
`847d44bfd2f09ffba0fcc71951e7604866ecbbae3a0397e8fc45e4bfacf38c91`.
This closes renderer consistency only, not retained backend/launcher authority.

Drain stdout and stderr concurrently as binary pipes. Do not merge, incrementally
decode, trim, normalize, extract fenced JSON or accept a valid prefix. Success
requires spawn success, no timeout or overflow, normal exit code zero, exactly zero
stderr bytes and nonempty stdout of at most 65,536 bytes. Empty stdout explicitly
sets `invocation_failed=true`. Only nonempty success bytes pass unchanged to the
existing strict parser and binder. Any spawn/exec
error, signal, nonzero exit, timeout, either overflow or any stderr byte sets
`invocation_failed=true`; exactly the first 65,537 stdout bytes are retained and
hashed while all later bytes are drained/discarded. They enter the
existing operational-failure path but cannot become success. Stderr content/hash
is discarded and never logged or persisted; at most 65,537 stderr bytes are
retained transiently only to establish overflow.

At timeout or overflow, send SIGTERM to the process group, keep draining for the
fixed grace, then SIGKILL the group, drain to EOF and reap exactly once. Process-
group cleanup is hygiene, not confinement; the isolation backend must deny fork,
the tested forbidden-exec operation must fail, and any permitted same-image
re-exec must remain confined without increasing process cardinality. CPU,
file-size and descriptor rlimits may add defense in depth,
but RSS, swap, Metal/ANE memory and thermal state are measurements, not guaranteed
limits. A native single-threaded launcher is required for any pre-exec rlimit work;
Python `preexec_fn` is forbidden.

Do not invent another semantic schema. Exact stdout feeds `bind_observation`; any
operational failure feeds its captured stdout plus `invocation_failed=true`.
Existing reason precedence remains `missing_anchor`, `invocation_failure`,
`malformed_json`, `forbidden_field`, `schema_violation`. A separate closed receipt
`aegis360.sparse-story-adapter-run-receipt.v1` has exactly `schema_version`,
`packet_id`, `inputs`, `execution`, `privacy`, `authority`; the exact nested keys,
types and invariants are frozen below. It contains no stderr, argv, env, path, PID,
signal, duration, exception or free text and must exact-rebuild as compact sorted
ASCII JSON.

The child cannot publish evidence. After it exits, the coordinator revalidates
the retained media tree and all immutable manifests, binds stdout, then exclusively
fsync-publishes receipt and evidence outside child scope. In every path it closes
pipes, terminates/reaps live children and descriptor-relatively deletes only
identity-proven owned scratch and transient input. Publication order is evidence,
receipt, then aggregate; none is authoritative without the final aggregate. Any
failure removes every already-published identity-owned peer. Replacements survive.
Publication or sensitive cleanup failure is `invalid`, not an abstention.

Synthetic coverage must include literal shell metacharacter argv, exact fresh env,
FD hygiene, cwd identity; stdout empty/invalid UTF-8/duplicate key/NaN/trailing
bytes and ceiling -1/exact/+1; concurrent pipe pressure; stderr, exit, signal,
timeout and TERM-ignore cases; child/grandchild containment; actual network and
forbidden read/write denial; scratch and allowed-input success; mutation and
replacement cleanup races; invocation cardinality, exact receipt rebuild and two
fresh byte-identical runs. Runner-operational aggregate precedence is `invalid`
for trust/isolation, schedule, forbidden-authority or cleanup failure; `reject`
for a deterministic behavior or repeatability miss; otherwise `pass`. Performance
completeness belongs only to the separate Stage A/B evaluation.

A pass proves only bounded one-shot local invocation under the tested synthetic
isolation contract with exact capture and cleanup. It proves no model identity
beyond manifests, semantic quality, real-output determinism, held-out validity,
source seeking, renderer correctness, performance suitability, boundary, chapter,
identity, camera, reorder, highlight or render behavior. No model acquisition or
real-media execution is authorized by this gate alone.

### Exact subordinate contracts

Seatbelt backend shape `aegis360.sparse-story-seatbelt-backend-manifest.v1`
has exactly `schema_version`,
`renderer_version=aegis360.seatbelt-policy-renderer.v1`, `host`, `backend`,
`launcher`, `system_rules`. `host` is exactly
`{operating_system:macOS,os_build,architecture:arm64}`; `os_build` is a
1..128-byte ASCII token matching `[A-Za-z0-9][A-Za-z0-9._-]*`. `backend` is
exactly `{logical_identity:com.apple.sandbox-exec,executable_sha256,
executable_size}` where size is a non-boolean integer 1..16 GiB. It describes
the OS-owned tool by content, never path. `launcher` is exactly
`{logical_identity:aegis360.native-process-launcher,runtime_manifest_sha256}`;
that separate runtime asset manifest and retained native proof own the
repo-controlled launcher's leaf sizes and identity. Neither fact may reuse the
asset proof's root-oriented `backend_identity()` name.

`system_rules` exact-rebuilds only this ordered list: `file-read*` subpaths
`/System/Library`, `/private/var/db/dyld`, `/usr/lib`; `file-read-data` literal
`/`; and `file-read-metadata` literal `/tmp`. It contains no sysctl, unobserved
system prefix, root subpath, temporary subpath or allow-default rule. Dynamic
paths never enter this manifest. Its shape/canonical JSON helpers convey no
filesystem, installation or execution authority; authoritative serialization,
derivation and validation require coordinator-owned retained proofs and remain
unavailable until implemented.

Renderer v1 accepts that exact shape plus exactly `runtime_root`,
`runtime_executable`, `forbidden_executable`, `bundle_root`, `model_root`,
`prompt_root`, `scratch_root`. Each is a canonical absolute control-free UTF-8
path of 1..4096 bytes and none is `/`; runtime executable is strictly beneath
runtime root. The five scoped roots are pairwise nonoverlapping and the forbidden
executable overlaps none in either direction. Exact output is ASCII with JSON
string escaping and final LF: version; deny default; sole process-exec literal
for runtime executable; deny fork; self process-info; one file-read rule with
runtime and forbidden-executable literals followed by bytewise-sorted subpaths
for runtime/bundle/model/prompt; the five system rules above; and the sole
scratch write subpath. No sysctl or allow-default line exists. These transient
bytes and their hash may bind a later token, but the pure renderer does not prove
installation or capability.

Runtime, model and prompt/schema assets use
`aegis360.sparse-story-asset-manifest.v1` with exactly `schema_version`,
`asset_kind`, `root_tree_sha256`, `entrypoint`, `entries`. `asset_kind` is
`runtime`, `model`, `prompt_schema` or `synthetic_support`; `entrypoint` is a safe relative path only
for runtime and null otherwise. `entries` is a bytewise-path-sorted list
of objects containing exactly string `relative_path`, non-boolean integer `mode`,
non-boolean integer `size` and lowercase SHA-256 `sha256`. A path has UTF-8 length
1..1024 and slash-separated segments matching
`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`, without dot segments. It is nonempty except
for `synthetic_support`, whose empty form has no leaves and root-tree SHA-256 equal
to SHA-256 of the empty byte string. Leaves are regular,
no-follow and link-count one; mode is 0444 except runtime entrypoint 0555. The
runtime entrypoint is additionally a directly executable native Mach-O for the
host architecture. V1 accepts only the 32-byte little-endian `mach_header_64`
with `MH_MAGIC_64=0xfeedfacf`, `CPU_TYPE_ARM64=0x0100000c`,
`CPU_SUBTYPE_ARM64_ALL=0` and `MH_EXECUTE=2`; every script, interpreter-mediated
entrypoint, swapped magic, other subtype/type/architecture and fat/universal
container is invalid before spawn. `sizeofcmds` must fit after the header,
`ncmds <= sizeofcmds/8`, and each retained-FD-read load command has size at least
eight, divisible by eight and within the table; their sizes consume the table
exactly. This proves format eligibility, not signature, loadability or behavior.
The directory set is exactly the root and required proper
ancestors, all 0555.
The retained implementation passed independent re-audit: it checks kernel
Darwin/arm64 facts, never requests more than the 32-byte header or one 8-byte
load-command header, revalidates retained and parent/name identity after hashing,
re-lists exact child maps after all leaves, and opens retained nodes CLOEXEC.
Synthetic huge-table, short-read, host mismatch and replacement-during-hash cases
fail closed. This grants format eligibility only.
Retained descriptors preserve every node's device/inode identity and each leaf's
size/timestamp evidence through the tree decision. Tree hashing reuses the media-tree line
grammar and identity rules. `model_asset_sha256` in semantic evidence is SHA-256
of canonical model-manifest bytes, not its content-tree digest.

Asset-tree traversal is bounded before hashing: at most 4,096 leaves and path depth
at most 16 segments. Every manifest size and matching leaf `fstat` size is at most
16 GiB, the declared and observed sums are each at most 64 GiB, and each leaf's
two sizes must equal; booleans are not sizes. All nodes share the root device and
recheck no-follow parent/name binding, type, `st_uid` equal to the coordinator's
effective UID, exact mode, device and inode. Leaves additionally recheck
`st_nlink=1`, declared size, frozen ctime/mtime and content SHA. Directories re-list
their exact child name/type/inode set; their size, nlink and timestamps are not
identity fields. Duplicate retained inodes and leaf/ancestor prefix conflicts fail.
These POSIX facts prove exact tree identity only; sandbox write denial, not 0444/
0555 or absence/presence of ACLs/xattrs, owns runtime immutability.

Runner policy `aegis360.sparse-story-runner-policy.v1` is path-free canonical JSON
with exactly `schema_version`, `backend_manifest_sha256`,
`timeout_ns=120000000000`, `termination_grace_ns=2000000000`,
`stdout_limit_bytes=65536`, `stderr_limit_bytes=65536`, `environment_template`
exactly `{"LANG":"C","LC_ALL":"C","TZ":"UTC","NO_COLOR":"1","HOME":"$PRIVATE_HOME","TMPDIR":"$PRIVATE_TMPDIR"}`, and
`capability_matrix_id=sparse-story-isolation-matrix-v1`. Its hash never contains
resolved HOME/TMPDIR or asset paths. A transient single-use capability token binds
that hash, launcher and exact enforcement-policy input bytes, uid/gid and retained root
device/inodes; it expires after one batch or any identity change.

Canonical stdin schema `aegis360.sparse-story-adapter-request.v1` has exactly
`schema_version`, `packet_id`, `projection`, `media`, `prompt_schema`, `model`.
The packet ID matches `packet-[0-9a-f]{20}` and projection exact-validates. `media`
is exactly six objects in projection row order containing only `media_ref` and
bundle-relative `path`, equal to that ref. Prompt/schema and model contain only
`manifest_sha256` and transient canonical absolute `root_path`; `prompt_schema`
also contains exact `prompt_path=prompt.txt` and
`schema_path=raw-observation-schema.json`, both validated manifest leaves. Each absolute
handle must resolve beneath its retained allowlisted root and exists only in stdin,
never stdout-derived or durable artifacts.

Capability receipt `aegis360.sparse-story-isolation-capability.v1` has exactly
`schema_version`, `backend_manifest_sha256`, `compiled_policy_sha256`,
`runner_policy_sha256`, `matrix`. `matrix` has exactly these boolean keys, all
true: `allowed_bundle_read`, `allowed_model_read`, `allowed_prompt_read`,
`allowed_scratch_write`, `denied_repository_read`, `denied_protocol_read`,
`denied_neighbor_packet_read`, `denied_result_read`, `denied_outside_write`,
`denied_process_fork`, `denied_process_exec`, `denied_ipv4`, `denied_ipv6`,
`denied_unix_socket`. Denial is an actual EACCES or EPERM; allow requires exact
sentinel bytes/action. The bound adapter runtime implements a closed
`--aegis-isolation-probe` mode; probes and inference invoke that same entrypoint
through the same launcher, uid/gid and byte-identical enforcement-policy input over the
same batch roots. The policy hash is bound in the token. Confinement is installed
before the one authorized entrypoint starts; subsequent fork is denied and exec
of the forbidden sentinel is denied, while threads and same-image re-exec remain outside
the denial claim as fixed above. Probe mode emits only a raw transcript. The trusted
coordinator constructs every boolean from exact sentinel bytes, EACCES/EPERM and
unchanged file/process/socket state; a child-printed `true` has no authority. Probe
mode cannot emit semantic output and does not count as an adapter inference invocation. Missing, skipped,
unavailable or erroneous probes are always `invalid` with zero adapter calls.

The run receipt's exact `inputs` keys are `adapter_projection_sha256`,
`sanitized_media_result_sha256`, `runtime_manifest_sha256`,
`model_manifest_sha256`, `prompt_schema_manifest_sha256`, `runner_policy_sha256`,
all lowercase SHA-256. `execution` contains exactly non-boolean integer
`invocation_count=1`, boolean `stdout_present`, lowercase `stdout_sha256`, boolean
`invocation_failed`; empty output hashes the empty byte string. `privacy` contains
exactly false `contains_source_path`, `contains_pixels`, `contains_audio`,
`contains_identity`, `contains_source_time`, `contains_free_text`. `authority`
contains exactly true `isolated_adapter_invocation` and false
`semantic_observation`, `exact_boundary`, `chapter_map`, `camera`, `reorder`,
`render`. Trust failure before spawn publishes no receipt/evidence and cannot be
downgraded because its aggregate row records invocation zero and `invalid`.

Final aggregate `aegis360.sparse-story-adapter-run-result.v1` has exactly
`schema_version`, `run_kind`, `inputs`, `packets`, `runner_outcome`, `privacy`,
`authority`. `run_kind` is `synthetic_gate`, `stage_a_smoke`, `stage_a_run_1`,
`stage_a_run_2` or `stage_b`; expected ordered packet counts are 1, 1, 6, 6 and 24.
`inputs` contains required lowercase hashes `schedule_sha256`,
`backend_manifest_sha256`, `runner_policy_sha256`, nullable
`compiled_policy_sha256`, nullable `capability_receipt_sha256`, nullable
`synthetic_adapter_manifest_sha256`, nullable `synthetic_case_manifest_sha256` and
nullable `synthetic_case_result_sha256`; the latter three are non-null only for
`synthetic_gate`. Inputs also contain `failure_stage`, exactly one of `none`,
`preflight`, `policy_compile`, `capability`, `invocation`, `publication`, `cleanup`.
Compiled-policy and capability hashes are non-null exactly after their respective
steps succeed; `failure_stage` names the earliest failure. For `synthetic_gate`,
adapter/case manifest hashes become non-null after their respective validation;
case-result hash becomes non-null only after every case and repeat completes.
`pass` or `reject` requires all three; early `invalid` requires every not-yet-
completed value null. Non-synthetic runs require all three null. Each ordered packet row contains exactly `packet_id`,
non-boolean integer `invocation_count` zero-or-one, and nullable lowercase
`receipt_sha256`, `evidence_sha256`. Count zero requires both null. Count one has
both hashes after complete publication, or both null only when publication/cleanup
is invalid and every owned partial peer was removed. `runner_outcome` is exactly
`invalid`, `reject` or `pass`. Privacy equals receipt privacy. Authority contains exactly true
`isolated_adapter_gate_result` and false `semantic_observation`, `exact_boundary`,
`chapter_map`, `camera`, `reorder`, `render`. This is runner-operational conformance
only; separate closed Stage A/B artifacts own semantic/scientific outcomes.

Synthetic fixture adapter uses the same closed runtime-manifest contract and its
canonical hash is the aggregate's `synthetic_adapter_manifest_sha256`. Direct argv
is exactly `[entrypoint,"--aegis-synthetic-case",case_id,"--",...stimulus.argv]`;
every string is passed literally without a shell and the suffix may be empty.
Normal invocation never accepts this option. Case selection is coordinator-owned. Synthetic case manifest
`aegis360.sparse-story-runner-cases.v1` contains exactly `schema_version`,
`synthetic_adapter_manifest_sha256`, `cases`, `repeat_packet_id`; each case contains
exactly `case_id`, `expected_result`, `stimulus`. `stimulus` is canonical JSON with
exact `argv`, `stdin_sha256`, `support_manifest_sha256`; the last value is SHA-256
of canonical `synthetic_support` manifest bytes, including the defined empty form.
Referenced stdin and support-tree bytes are hash-bound and validated before execution. `cases` follows
the exact ordered `case_id`/`expected_result` sequence frozen below. Result
`aegis360.sparse-story-runner-case-result.v1` contains exactly `schema_version`,
`case_manifest_sha256`, `cases`, `repeatability`. Each ordered case contains only
`case_id`, `expected_result`, `observed_result`, `passed`; IDs/order/expected values
must exactly equal the manifest, `observed_result` uses the same closed enum, and
`passed` is exact equality. `repeatability` contains only `packet_id`,
`first_stdout_sha256`, `second_stdout_sha256`, `equal`; `equal` is hash equality.
The result hash is bound by the synthetic aggregate and its packet ID equals both
the manifest repeat ID and synthetic schedule packet.

The closed result enum is `success`, `malformed_json`, `forbidden_field`,
`schema_violation`, `invocation_failure`, `isolation_denied`,
`isolation_allowed`, `trust_invalid`, `replacement_preserved`, `exact_rebuild`.
The exact ordered manifest is:

```text
argv_literal:success, environment_exact:success, fd_hygiene:success,
cwd_identity:success, stdout_empty:invocation_failure,
stdout_invalid_utf8:malformed_json, stdout_duplicate_key:malformed_json,
stdout_nan:malformed_json, stdout_trailing_bytes:malformed_json,
stdout_forbidden_field:forbidden_field, stdout_extra_field:forbidden_field,
stdout_limit_minus_one:success, stdout_limit_exact:success,
stdout_limit_plus_one:invocation_failure, concurrent_pipe_pressure:success,
stderr_nonempty:invocation_failure, nonzero_exit:invocation_failure,
signal_exit:invocation_failure, wall_timeout:invocation_failure,
term_ignore_kill:invocation_failure, grandchild_containment:isolation_denied,
network_ipv4_denied:isolation_denied, network_ipv6_denied:isolation_denied,
unix_socket_denied:isolation_denied, repository_read_denied:isolation_denied,
protocol_read_denied:isolation_denied,
neighbor_packet_read_denied:isolation_denied,
result_read_denied:isolation_denied, outside_write_denied:isolation_denied,
bundle_read_allowed:isolation_allowed, model_read_allowed:isolation_allowed,
prompt_read_allowed:isolation_allowed, scratch_write_allowed:isolation_allowed,
bundle_mutation:trust_invalid, replacement_race:replacement_preserved,
single_invocation:exact_rebuild, receipt_rebuild:exact_rebuild
```

Aggregate derivation is total: invalid trust/lineage/media/manifest/policy,
capability miss, schedule/cardinality error, forbidden authority, partial
publication or sensitive cleanup failure is `invalid`; any deterministic fixture
or byte-repeat miss is `reject`; otherwise `pass`. Measurement completeness is
owned only by separate Stage A/B artifacts. The
synthetic schedule is one valid packet; negative cases produce only their in-memory
case rows and no per-case run artifact. Every scheduled batch publishes one final
aggregate when its destination is usable. A batch-wide trust/capability failure
records all scheduled rows with invocation zero, null hashes and `invalid`; failure
to publish that aggregate is an externally reported invalid operation, never an
inconclusive artifact. Stage A is
one separate one-packet smoke followed by two complete runs of six serial one-
packet invocations, each in a fresh process group: 13 calls overall, only the
latter 12 entering correctness and repeatability.

## Stage A: bounded feasibility

Freeze exactly six known-label diagnostic packets: Old Ghost 205.6-second story
change and 132.4-second no-change; Skiing second-200 story change, 297-second
no-change, 327.25-second stitch/stretch artifact and 386.5-second no-change.
These are a predeclared feasibility/regression set, not held-out accuracy data.
Their labels are intentionally public in this protocol but are absent from the
adapter-visible projection. Stage A therefore makes no hidden-key or held-out
claim. To prevent the public labels from entering inference, its execution
worker receives only the sanitized projections, frozen prompt/schema, frozen
model runtime and an opaque output destination; it has no repository, protocol,
conversation history, label key, prior output or network access. Freeze packet
set, neutral schedule, model asset and prompt/schema before inference.

Run one packet in one fresh process as an operational smoke only, then run two
independent complete six-packet runs. Each complete run is serial and each packet
uses its own fresh process group, for exactly 12 complete-run invocations. The
smoke does not count toward either complete run. Freeze exactly 12 raw-output hashes
for the two complete runs. Record wall time, process RSS, MLX peak memory, swap
and thermal state on the M4 MacBook Air with 16 GB. The complete runs must
produce byte-identical closed output per matching packet. Malformed output,
any forbidden field or model failure follows the operational-
failure contract and becomes a failure-bound abstention.

There are exactly two story, three no-change and one artifact cases. Both story
cases, all three no-change cases and the artifact must be correct; abstain or
model failure counts incorrect. Outcome precedence is total: invalid lineage,
packet/key composition mismatch, label leakage into adapter-visible input or
forbidden downstream authority, missing/partial runner receipt or evidence yields
`invalid`; after complete valid runner artifacts, missing required non-security
performance measurements yields `inconclusive`; missing/empty model stdout follows
invocation failure and counts incorrect. Otherwise non-identical reruns
or any incorrect case yields `reject`; otherwise the result is `pass`. No
outcome permits prompt edits on these packets. This stage cannot support
generalization.

## Stage B: source-diverse blind gate

Only after Stage A passes, freeze Skiing, Bellpuig, Gaudeamus and Hundra. For
each source, the proposal universe is every event in its frozen multi-signal
union timeline after overlap-cluster local deduplication only. An event is
eligible when all six packet rows at offsets `-15`, `-3`, `-0.25`, `+0.25`,
`+3` and `+15` seconds are within the source. Order eligible proposals by the
ascending SHA-256 digest of the exact UTF-8 string, with no trailing newline,
`source_sha256|timeline_sha256|stage-b-proposal-v1|event_id`; break a digest tie
by bytewise event ID. Greedily take the first three whose centers are at least
30 seconds from every already selected proposal center.

Build the control universe from the fixed ten-second lattice at 20.0, 30.0,
... seconds through the last lattice point no later than source duration minus
20 seconds. First remove points whose absolute distance from any selected
proposal is less than 30 seconds. Order the survivors by the ascending SHA-256 digest
of the exact UTF-8 string, with no trailing newline,
`source_sha256|timeline_sha256|stage-b-control-v1|timestamp_one_decimal`; break
a digest tie by numeric timestamp, then greedily accept a point only when its
distance from every already accepted control is at least 30 seconds, stopping
after three. Freeze
the exact timeline, dedup clusters, eligible universes, order keys, exclusions
and selected proposal event IDs plus selected control timestamps in their pre-
projection selection order in an execution manifest. Fewer than three proposals
or controls for any source makes the run `inconclusive`; there is no replacement
or backfill. The complete set is therefore exactly 24 packets.

Freeze the execution manifest, private lineage packets, adapter-visible
projections, model asset, prompt/schema and two fresh isolated reviewers'
instructions. Reviewers receive only the review media and label all 24 packets;
their output hashes are frozen while their contents remain unavailable to the
model operator. Run exactly one complete model pass and freeze all 24
per-packet raw-output hashes. Each packet's single bound class from that pass
enters the semantic numerator. Only then may the coordinator open the reviewer
outputs and proposal/control mapping.

Adequacy requires all 24 reviewer pairs to agree on binary story/no-change,
at least six of each overall, both classes in at least two sources and at least
four nuisance no-change packets. A packet belongs to the nuisance denominator
only when both reviewers label it no-change and both independently mark
`viewpoint_change=present` or both independently mark
`foreground_rearrangement=present`; agreement on one of those fields suffices.
Artifact, abstention, disagreement or inadequate balance makes the run
inconclusive; it does not authorize more samples.

Let `N_story`, `N_no_change` and `N_nuisance` be the adequate unanimous reviewer
denominators. Proposal recall passes only when proposed story packets divided
by `N_story` is at least `5/6`, and every source containing a story packet has
at least one proposed story packet. Semantic discrimination passes only when
correct story predictions divided by `N_story` is at least `5/6`, correct
no-change predictions divided by `N_no_change` is at least `5/6`, and correct
nuisance-negative predictions divided by `N_nuisance` is at least `3/4`.
For the nuisance numerator, a prediction is correct exactly when the binder
emits `no_semantic_change`; matching the reviewers' nuisance subtype is not
required.
Model failure, malformed output, artifact classification or abstention counts
incorrect against every applicable adequate denominator.

Outcome precedence is fixed. Invalid lineage, leakage before reveal,
unscheduled inference or forbidden authority yields `invalid`. An adequacy or
selection-capacity failure yields `inconclusive`. With adequate data, both
proposal recall and semantic discrimination must pass for overall `pass`;
otherwise the result is `reject`. Evaluate categorical results only; do not
search a numeric threshold, discard hard packets or revise the prompt.

## Stop conditions

Reject cheap-signal recall when its frozen Stage B fraction misses `5/6` or any
story-bearing source has zero recall. Reject semantic discrimination when either
binary class or nuisance specificity misses its frozen bound. Mark the run
invalid if inference consumes unscheduled frames or emits boundary, camera,
time-reorder or render authority. Gradual changes missed by every cheap signal
remain an explicit recall gap even if the semantic classifier passes.
