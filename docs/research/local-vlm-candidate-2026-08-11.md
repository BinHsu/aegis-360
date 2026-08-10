# Local VLM candidate — 2026-08-11

Status: Proposed only; acquisition is not authorized

## Need

Classify a bounded short window as conversation/group/context and select one
geometry-owned proposal or return uncertain. The model must run offline on the
M4 MacBook Air with 16 GB unified memory. It must not output camera geometry,
identity or durable free text.

## Leading candidate

`HuggingFaceTB/SmolVLM2-500M-Video-Instruct`, using the MLX BF16 conversion
`mlx-community/SmolVLM2-500M-Video-Instruct-mlx`, is the first candidate.

Reasons:

- the upstream model card explicitly supports video and multi-image input;
- the upstream and MLX conversion model cards both claim Apache-2.0;
- upstream reports 0.5B parameters and about 1.8 GB GPU RAM for video inference;
- the MLX conversion is listed as BF16 and about 1.02 GB;
- Hugging Face documents Apple-Silicon video inference through MLX, while
  MLX-VLM documents video support and an MIT runtime license.

Primary sources:

- <https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct>
- <https://huggingface.co/mlx-community/SmolVLM2-500M-Video-Instruct-mlx>
- <https://huggingface.co/blog/smolvlm2>
- <https://github.com/Blaizzy/mlx-vlm>

## Rejected as first candidate

Apple FastVLM 0.5B is attractive for fast visual encoding and has an official
MLX path, but its model card primarily reports image benchmarks rather than
video understanding, and the weights use the Apple AMLR license rather than
Apache-2.0. It remains a possible per-frame fallback, not the first short-window
candidate: <https://huggingface.co/apple/FastVLM-0.5B-fp16>.

## Pinned metadata

Read-only Hugging Face API metadata on 2026-08-11 reports:

- upstream revision `7b375e1b73b11138ff12fe22c8f2822d8fe03467`;
- MLX conversion revision `fa57db46815177fbdfd65cc85a2b3416a8332268`;
- MLX repository storage of 1,015,023,993 bytes (about 968 MiB).

This is a download estimate, not locally measured acquired bytes. Individual
file checksums still must be measured after explicit acquisition.

## Required before acquisition

Review conversion provenance and all license texts, then obtain explicit
authorization for roughly 1.02 GB of model assets plus the runtime dependency.
After acquisition, measure checksum, byte size, cold/sustained latency, peak
RSS, swap and output stability. Compare a deterministic multi-image sample
against video decoding so the model never needs the full source path or an
unbounded clip. Treat prompt-only JSON as untrusted and pass it through the
closed importer.
