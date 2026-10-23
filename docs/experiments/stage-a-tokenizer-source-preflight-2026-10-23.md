# Stage A tokenizer source preflight

Date: 2026-10-23. This is a source-only inventory. No tokenizer package was
built, resolved by SwiftPM, installed or run. Source checkouts are retained
under the approved T7 `aegis-360-items/sources/` area, outside Git.

The official `huggingface/swift-transformers` 1.3.0 tag resolves to commit
`b38443e44d93eca770f2eb68e2a4d0fa100f9aa2`, tree
`b973309bc7bad3c28d94a74344f3075cb2d8c77f`, with a clean checkout and
236 reachable commits. Its Swift 6.1 manifest declares `swift-jinja`,
`swift-xet`, `swift-huggingface`, `swift-collections`, `swift-crypto` and
`yyjson`; ranges are not an exact resolution lock. The local-directory
`AutoTokenizer.from(modelFolder:)` API is documented by upstream.

Source-only companion checkouts at public tags are:

| Package | Tag | Commit | Tree |
|---|---|---|---|
| huggingface/swift-jinja | 2.0.0 | `1e6f84d6fca8ee93217b5594ce2025cbb0209c3a` | `599b0d85243c0e2270b98a46da89c502f2227fe8` |
| huggingface/swift-xet | 0.2.0 | `6185aea25aa25e78197d78bd776b92b199aa82fb` | `c25c2029da73f2a2237bb962cbb55694abb686af` |
| huggingface/swift-huggingface | 0.9.0 | `b721959445b617d0bf03910b2b4aced345fd93bf` | `44eb5c7981ba6d811c30d67b541c00a65dd19735` |
| huggingface/swift-huggingface | 0.8.1 | `de01c0ab8fd537bbd8216cea7f774275178501a2` | `b9eaca8c707896f9973e3bae3acfa9a415b45c72` |
| apple/swift-collections | 1.0.0 | `07e47b1e93e5a1e0ef0c50fcb2d6739fb6be4003` | `02fe25fa7e8157f94d0d720671e9174eac5c3a26` |
| apple/swift-crypto | 3.0.0 | `629f0b679d0fd0a6ae823d7f750b9ab032c00b80` | `ec492f6af9366c332f1d0ec82b3c77a8b0ef2660` |
| ibireme/yyjson | 0.12.0 | `8b4a38dc994a110abaec8a400615567bd996105f` | `a51e8386f5e259392d2a77ee2300ea17210f5fa1` |
| mattt/EventSource | 1.3.0 | `ca2a9d90cbe49e09b92f4b6ebd922c03ebea51d0` | `bcec2e0ed0b831633924112cff88b100e7f7e0bd` |

The 1.0.0 EventSource tag was also inspected but rejected for adoption:
its two-commit history begins with the complete implementation, triggering
the `supply-chain-audit` stop signal. EventSource 1.3.0 has 19 reachable
commits and no declared package dependency. The 1.5.1 source was inspected
but introduces optional AsyncHTTPClient/NIO dependencies and was not selected.

The selected top-level source licenses read as Apache-2.0 for
swift-transformers, swift-jinja, swift-huggingface, swift-collections and
swift-crypto; MIT for yyjson and EventSource 1.3.0. `swift-xet` has no
top-level LICENSE in its pinned source and is not approved for execution.
The inspected manifests have no SwiftPM plugin, binary target, system
library or unsafe-flags declaration. `swift-huggingface`'s Swift 6.0
manifest enables Xet; its plain manifest makes Xet conditional. No local
manifest rewrite or dependency build has been made yet.

Tool coverage is limited: Trivy's offline result reported no target scanned,
Syft's CycloneDX output identified workflow metadata rather than a resolved
Swift graph and attempted a blocked version check, and Semgrep `--config auto`
failed before scanning because the local trust store had no anchors. These
are not clean security results. The exact resolved graph, transitive source
audits, executable tokenizer adapter, native isolation proof and model
invocation remain open.

Follow-up on 2026-10-24: the exact 1.0.0 Collections source failed under
Swift 6.4, so Apple's 1.7.2 tag was separately audited and used in an
isolated offline graph. Optional Xet was excluded. The resolved graph,
successful tokenizer target build and local round trip are recorded in
`stage-a-tokenizer-offline-build-2026-10-24.md`. This does not revise the
source-only status of the older checkouts or imply a model invocation.
