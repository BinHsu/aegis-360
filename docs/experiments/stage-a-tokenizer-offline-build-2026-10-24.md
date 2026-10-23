# Stage A offline tokenizer build and local smoke

Date: 2026-10-24. Host: Apple M4 MacBook Air, macOS 27.0.1, Xcode 27.2 RC
(27B48). All sources, caches, scratch and products were under the approved
T7 project root. The build and smoke ran under outer `sandbox-exec` network
denial; SwiftPM's nested sandbox was disabled after its `sandbox_apply`
returned `Operation not permitted` under that outer policy.

The first exact local graph used `swift-collections` 1.0.0, the minimum
declared by `swift-transformers` 1.3.0. The tokenizer target failed after
14.0 seconds: `swift-jinja` 2.0.0 captured `OrderedDictionary` in Sendable
contexts, while that Collections release did not provide the required
Sendable conformance. The v2 stage, build log and failed status remain on
T7. No tokenizer executable or model invocation resulted.

Apple's [official Collections release notes](https://github.com/apple/swift-collections/releases/tag/1.7.1)
identify 1.7.1 as carrying a
Swift 6.4 workaround; 1.7.2 was selected and pinned at commit
`3b69cedbaa49957e97c092ae400bb57602ef941f`, tree
`3cd3fc6ac51c4626c8fa7f9f2cab94760ca9e40e`. Its checkout is clean,
has 1,996 reachable commits, Apache-2.0 license and no declared package,
plugin, binary target or unsafe flags in its inspected manifests.

`scripts/prepare_stage_a_tokenizer_snapshot.py` copied seven exact source
trees into a new v3 T7 stage after checking their commits and per-file
digests. It disabled version-specific manifests in the isolated copies,
used each package's reviewed plain manifest, replaced remote package
declarations with sibling local paths, and excluded optional Xet transport.
The original tagged checkouts were not changed. The stage's
`source-manifest.json` retains commit, Git tree, source-copy digest and
manifest hash for each package. An initial v1 preparation stopped before
emitting a manifest because a comment URL was mistaken for a package URL;
that partial stage remains on T7. The v3 checker looks for `.package(url:`.

Every selected SwiftPM manifest was evaluated under network denial. The
resolved graph contains only `swift-transformers`, `swift-jinja`,
`swift-huggingface` 0.9.0, `swift-collections` 1.7.2, `swift-crypto` 3.0.0,
`yyjson` 0.12.0 and `EventSource` 1.3.0; no remote dependency remained.
The graph includes no `swift-xet` package. The source-only audit and scanner
coverage limits are in
`stage-a-tokenizer-source-preflight-2026-10-23.md`.

`scripts/build_stage_a_tokenizer_v3.py` checked those manifest hashes and
the resolved graph, then built the `Tokenizers` target with two jobs in
18.7 seconds. The log ends with `Build of target: 'Tokenizers' complete!`.
SwiftPM warns that its native backend is deprecated; no successor build
route was verified here.

`scripts/run_stage_a_tokenizer_smoke.py` rechecked the local SmolVLM2 2.2B
asset tree and built a separate executable against that local graph. The
executable called `AutoTokenizer.from(modelFolder:)` on the existing T7
directory, encoded and decoded `hello world` with no special tokens, and
exited zero with `local tokenizer round trip: 2 tokens`. The build plus run
took 24.7 seconds. The v3 and smoke stages retain logs and status files.

This proves a local tokenizer load and one round trip. It does not prove
image processor compatibility, full model loading, semantic inference,
resource isolation for a private Stage A packet, or sustained performance.
