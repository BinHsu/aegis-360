# Stage A SmolVLM2 prepared input path — 2026-10-30

## Question

Could the guided candidate's 3/6 known-label result be caused by dropping or
reordering the six frames, omitting image tokens, or placing the video text
after the assistant generation prompt? The prior processor smoke counted
frames and tokens but did not inspect post-preprocessing pixel order or prompt
position. This probe is model-free and uses only six generated solid-color
images, the frozen local tokenizer and processor metadata, and no private
media or weight inference.

## Method and result

`tools/stage_a_vlm/smol_processor_smoke.swift` now gives the six frames
strictly increasing red values. After the pinned `SmolVLMProcessor` prepares
the input, it requires a `[6,384,384,3]` pixel tensor, six strictly increasing
red samples at the same interior coordinate, six frame descriptors, exactly
486 image tokens, the frozen system prompt, and the video frame prompt between
`User: ` and the final `Assistant:` generation marker. Each check can fail on
a distinct wrong shape, lost/reordered image or misplaced video prompt.

A fresh offline network-denied T7 build/run under `build/stage-a-smol-processor-v3/`
exited zero after 105.921 seconds and printed the expected pass line. Its
source and prompt hashes are in the local `status.json`; the source probe hash
is `2649c20f1ca9b5aa394a9e63df91480c1e07112f25d1a3f9b69f2bdb9bb529f9`.
The upstream SmolVLM2 processor samples six requested video frames across
synthetic timestamps 0–5, resizes and normalizes them, and returns the pixel
tensor in `LMInput.image`. The guided loop passes that `LMInput` to the model's
`prepare` method, which is the Idefics3 implementation for this SmolVLM2
configuration. This source trace is consistent with the executed probe.

## Interpretation

The tested synthetic path does not drop or reorder frames, omit image tokens,
or append the video prompt after the assistant marker. The known-label
failure remains unexplained. The probe does not inspect actual private-frame
visual quality, quantify model attention to image embeddings, or establish
that the frozen wording matches what the model can reliably classify. Any
changed treatment needs a new independent holdout; the six known packets are
now diagnostic examples.
