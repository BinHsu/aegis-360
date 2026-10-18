# MLX Swift LM 3.32.3 source-only audit

Status: bounded source review; no build, dependency resolution, imported code
execution or model inference.

## Scope and provenance

The owner explicitly approved fetching official `ml-explore/mlx-swift-lm`
`3.32.3` source for an isolated audit. `git ls-remote` returned commit
`3b339ad6e3b3f44c8121ecff5131c7fd55e075e6` for that tag. A shallow,
single-tag source checkout under `/private/tmp` resolved to the same commit;
tree `bbba5542694fbf2eaa3e8cfd053aa0e7edb8f79b`, 654 tracked files,
clean worktree. Remote was `https://github.com/ml-explore/mlx-swift-lm.git`.
The commit carries a GitHub GPG signature, but `git verify-commit` could not
establish trust: the sandbox could not access local GnuPG keyboxd and no public
key was available. The tag is lightweight in this checkout.

After inspection, the source checkout was copied to
`/Volumes/T7/aegis-360-items/sources/mlx-swift-lm-3.32.3`.
Readback there matched the full commit and tree above and had a clean Git
status. The scratch copy was not deleted; it is not the canonical build source.
No dependency or build output has been created by this audit.

Source: <https://github.com/ml-explore/mlx-swift-lm/tree/3.32.3>.
`Package.swift` SHA-256:
`2b6698d6625eb832aacf4ec59ed32f587e7ae06f3020932ce6a70b9483abc02a`.

## Static findings

| Question | Observation | Limit |
| --- | --- | --- |
| License | Root `LICENSE` is MIT; vendored xgrammar tree has Apache-2.0 `LICENSE` and `NOTICE`. | Dependency and model licenses remain separate. |
| Toolchain | Manifest requires Swift tools 6.2 and macOS 14+. Host CLT provides Swift 6.4. | No package evaluation/build occurred; Xcode app is not selected. |
| Runtime graph | Main declared packages are official `ml-explore/mlx-swift` `0.32.3` up to next minor and `swiftlang/swift-syntax` `602.0.0` to below `604.0.0`. `swift-docc-plugin` from `1.3.0` is appended when documentation environment variables are set. | No `Package.resolved`; exact revisions and transitives are unknown. |
| Build surface | `MLXHuggingFaceMacros` is a Swift compiler macro target. `MLXCXGrammar` compiles vendored xgrammar C++ and applies `-w` unsafe flags on Apple platforms. Vendored version file names xgrammar `v0.1.30`, informational SHA `d476a48dcd8fa3b5afeddbe850e73bb3b1dcf505`. | Vendored source identity and full compile behavior are unverified. |
| Local model | VLM factory maps `smolvlm` to `SmolVLM2`; processor registry includes `SmolVLMProcessor`. The installed T7 model's config declares both strings. Common factory exposes a local-directory load path with no downloader argument. | No Swift adapter, tokenizer load, weight mapping, offline behavior or output validated. |
| Hooks and binaries | Tracked tree has no `Package.resolved`, `.gitmodules`, Makefile, `.githooks`, prebuilt dylib or xcframework. Scripts include xgrammar sync and docs verification, neither executed. | Manifest, macro, C++ compilation and dependencies still require review before build. |

## Static scanner coverage

- Syft generated a local CycloneDX inventory with 15 components, all workflow
  action/workflow entries. It did not inventory the Swift manifest dependencies
  or vendored C++; it is not a complete dependency SBOM.
- Trivy ran with `--offline-scan --skip-db-update --skip-java-db-update` and
  vulnerability/secret scanners. It reported zero language-specific files and
  zero result records. This is no vulnerability clearance.
- Semgrep failed before scanning, while initializing the local system X509
  authenticator (`ca-certs: empty trust anchors`). No Semgrep result exists.
- No Swift ecosystem vulnerability audit ran because the exact dependency
  graph was not resolved. No networked scanner update was requested.

## Decision boundary

The source-only acquisition is complete. Building a native adapter requires a
separate bounded acquisition of exact Swift dependency sources and a review of
their manifests, licenses, hooks, vendored code and offline behavior. The
macOS 27.0.1 `sandbox-exec` backend remains fail-closed independently; static
source compatibility grants no native invocation authority. Do not infer a
Stage A semantic result from this audit.
