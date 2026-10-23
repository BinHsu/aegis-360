# Stage A local VLM tokenizer bridge

Date: 2026-10-24. Host: Apple M4 MacBook Air, macOS 27.0.1, Xcode 27.2 RC (27B48). Source, cache, scratch, products and logs remained under `/Volumes/T7/aegis-360-items/build/`. All graph, build and smoke commands ran under outer `sandbox-exec` network denial with SwiftPM's nested sandbox disabled.

`scripts/run_stage_a_vlm_bridge_smoke.py` combined the already pinned local `MLXVLM` and `Tokenizers` package snapshots. The resolved combined SwiftPM graph contained no remote URL. `tools/stage_a_vlm/TokenizerBridge.swift` implements the `MLXLMCommon.Tokenizer` interface using the local Hugging Face `AutoTokenizer.from(modelFolder:)` loader. It includes chat-template handling and maps the missing-template error. The executable does not load model weights or images.

The v1 stage failed because a multi-file Swift executable had an `@main` declaration in `main.swift`; its failed build was preserved. The v2 stage built and produced `local VLM tokenizer bridge: 2 text tokens, 9 chat tokens`, but a missing-directory negative control emitted a Swift error diagnostic. The v3 source catches that input error and exits with code 5 and exactly `bridge input error\n`.

The v3 isolated build and two runs completed in 101.665 seconds. The positive smoke again emitted `local VLM tokenizer bridge: 2 text tokens, 9 chat tokens`. The missing-directory negative control exited 5 and emitted the exact controlled error. The stage status is `success`; its source hashes are `1869155c2c7a1b96e4188ac2ff697d3b4171b17f3e4740e14488b0ee0df397ca` for `TokenizerBridge.swift` and `3d8e6598af47395f1b472d2a5e67630da8bf3de3cf001e7b5ab999828e5051ba` for `bridge_smoke.swift`. Logs and status are retained at `/Volumes/T7/aegis-360-items/build/stage-a-vlm-bridge-v3/`.

This verifies a local tokenizer interface and chat-template call across the pinned package graphs. It does not verify image processing, full model loading, private-packet isolation, semantic output, or performance. No model ran.
