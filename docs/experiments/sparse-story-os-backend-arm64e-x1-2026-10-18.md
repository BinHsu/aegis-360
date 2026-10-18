# macOS 27.0.1 OS-backend Mach-O subtype review

Status: retained backend proof passed on this host; no semantic adapter or
model invocation.

## Question and evidence

Could the frozen backend parser validate the installed two-slice
`/usr/bin/sandbox-exec` without accepting an unknown ARM64 executable slice?
The installed Command Line Tools SDK's `mach/machine.h` names subtype 2
`CPU_SUBTYPE_ARM64E` and subtype 12 `CPU_SUBTYPE_ARM64E_X1`; both use the
`0x80000000` pointer-authentication ABI capability bit in this binary.
`file`, `lipo -detailed_info` and `otool -hv` agree that the installed fat32
executable has exactly those two slices, each `MH_EXECUTE`. Its whole-file
SHA-256 was `58839ef01b4eef8aac0d2aa8f9d1c074ae45aafe3533965b030672450064acc8`.
The host reports macOS 27.0.1 build `26A434`.

The parser now accepts only a lone raw `0x80000002` ARM64E slice or the exact
pair `{0x80000002, 0x8000000c}`. It validates the thin header and bounded load
commands of **each** ARM64 slice and still rejects duplicate, overlapping,
unknown or lone ARM64E_X1 layouts. This change does not select a slice or
claim to predict the kernel's selection: both possible host ARM64 slices must
meet the same structural predicate. The retained proof still hashes and
revalidates the entire frozen file and its filesystem/build facts.

## Discriminating checks

- A controlled run of the previous committed validator against the installed
  file rejected it with `host ARM64 raw subtype is invalid`; the changed
  validator accepted that same file.
- A synthetic pair with a second fat-row/thin-header mismatch fails with
  `ARM64 slice identity is invalid`; unknown raw subtype `0x8000000d` and a
  lone ARM64E_X1 fail. Prior duplicate/overlap/command negative controls pass.
- Focused parser suite: 17 tests, one expected host-only skip. Explicit host
  observation with `AEGIS_RUN_HOST_OS_BACKEND_TESTS=1`: one pass; it opens,
  revalidates and closes the real retained backend proof.
- Full portable discovery: 947 tests, 97 skipped, no failures.

`codesign --verify` returned `CSSMERR_TP_NOT_TRUSTED` for the ARM64E_X1 slice
in this sandbox. The proof never claimed cryptographic signature validation;
this output is not a successful signature check. The existing
read-only/restricted APFS and pathname-reopen limitations remain. Passing
this backend proof alone grants no installed-policy, adapter or model
invocation authority.
