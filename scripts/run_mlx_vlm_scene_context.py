#!/usr/bin/env python3
"""Run bounded local MLX-VLM inference and atomically emit scene-context v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.local_context_adapter import build_local_context_document  # noqa: E402
from aegis360.local_context_schema import local_context_json_schema  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal_json", type=Path)
    parser.add_argument("model_directory", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("frames", nargs="+", type=Path)
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    parser.add_argument("--maximum-frames", type=int, default=4)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if not 1 <= len(args.frames) <= args.maximum_frames <= 8:
        parser.error("frame count must be within the declared bound")
    if not args.proposal_json.is_file() or not all(path.is_file() for path in args.frames):
        parser.error("required proposal or frame is missing")
    weight = args.model_directory / "model.safetensors"
    if not weight.is_file() or sha256_file(weight) != args.expected_model_sha256:
        parser.error("model asset SHA-256 mismatch")

    from mlx_vlm import generate, load
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.structured import build_json_schema_logits_processor

    proposal = json.loads(args.proposal_json.read_text(encoding="utf-8"))
    schema = local_context_json_schema(proposal, audio_provided=False)
    started = time.monotonic()
    model, processor = load(str(args.model_directory))
    prompt = apply_chat_template(
        processor, model.config,
        "Classify the visible scene. Conversation means people visibly talking or socially interacting. Coordinated activity means people jointly performing a physical task. Ambient people means people are present without clear interaction. Prefer a group proposal when multiple interacting people should remain visible. Use unknown when evidence is not visually established. These are silent image samples, not audio input.",
        num_images=len(args.frames),
    )
    constrained = build_json_schema_logits_processor(processor.tokenizer, schema)
    result = generate(
        model, processor, prompt, image=[str(path) for path in args.frames],
        temperature=0, max_tokens=160, logits_processors=[constrained],
        verbose=False,
    )
    decision = json.loads(result.text)
    document = build_local_context_document(
        proposal, decision, adapter_id=args.adapter_id, model_id=args.model_id,
        model_sha256=args.expected_model_sha256,
    )
    runtime_evidence = {
        "frame_count": len(args.frames), "audio_provided": False,
        "elapsed_seconds": time.monotonic() - started,
        "generation_tokens": result.generation_tokens,
        "mlx_peak_memory_gb": result.peak_memory,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.output_json.parent,
        prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
    ) as temporary:
        temporary_name = temporary.name
        temporary.write(json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n")
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    print(json.dumps(runtime_evidence, allow_nan=False, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
