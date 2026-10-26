# Stage A retained adapter probe

Date: 2026-10-26. Host: M4 MacBook Air, macOS 27.0.1, Xcode 27.2 RC (27B48). All build scratch, products and probe temporary state were under `/Volumes/T7/aegis-360-items/`. No model weights or private packets were read by these probes.

The v3 Stage A executable embeds the repository's synthetic C probe entry in the same Mach-O image as the Swift model entry. A closed `--aegis-synthetic-case` argument dispatches to the C probe; ordinary launch continues through the request parser. The existing standalone C fixture retains its default `main` entry. The v3 offline SwiftPM build succeeded in 106.285 seconds with network denied and passed an invalid-request silent exit and a direct empty-output probe. Its 74,323,776-byte signed thin ARM64 executable has SHA-256 `46df29bc002f7c34f2b8efcc61767716567a40a31e73752f4b886d2b6a53cdd0`. The strict runtime asset tree passed readback against `stage-a-native-adapter-runtime-v3-manifest.json`, digest `db2108c6878d7f69ff4c0d0beb5599b3fcf058ef0508a8d2bbc34f7057f14eaa`. The original Metal library remains SHA-256 `8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59`. Strict code-sign verification passed.

`run_stage_a_restricted_probe_smoke.py` bound the retained T7 launcher, forbidden-exec sentinel and v3 adapter by exact saved manifests, then used the production native transport and generated policy with synthetic bundle/model/prompt input. Its first attempt misclassified the deliberately empty `stdout_empty` case: the transport correctly returns `native_process_invalid` when stdout is empty. That attempt retained its result at `build/stage-a-restricted-probe-v1/status.json`; it was not reused. The corrected v2 run completed in 1.089 seconds:

| Case | Exit | Transport complete | Group gone | Postcheck | Output |
|---|---:|---|---|---|---:|
| `stdout_empty` | 0 | false, expected rejection | true | true | 0 bytes |
| `environment_exact` | 0 | true | true | true | 378 bytes |

The script asserted the row values and exited successfully. Nine existing standalone synthetic-fixture tests also ran without failure; three listener tests were skipped because this host policy denied local bind. These checks prove a restricted launch of the **combined executable** and one environment probe. They do not prove the full 14-row isolation matrix, complete 37-case coordinator, valid private request, model loading, semantic output, or throughput. The full isolation and input-authority gates remain before any private model invocation.
