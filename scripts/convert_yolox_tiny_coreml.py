#!/usr/bin/env python3
"""Convert an external YOLOX-Tiny checkpoint and compare raw zero-input output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def write_output(path: Path, values, shape, detections) -> None:
    document = {
        "tensors": [{
            "name": "raw_head",
            "shape": list(shape),
            "values": values.reshape(-1).tolist(),
        }],
        "detections": detections,
    }
    path.write_text(
        json.dumps(document, allow_nan=False, separators=(",", ":")) + "\n"
    )


def fixtures(torch):
    width = 416
    horizontal = torch.linspace(0, 1, width).view(1, 1, 1, width)
    vertical = torch.linspace(0, 1, width).view(1, 1, width, 1)
    generator = torch.Generator().manual_seed(360)
    return {
        "zeros": torch.zeros(1, 3, width, width),
        "midgray": torch.full((1, 3, width, width), .5),
        "horizontal-gradient": horizontal.expand(1, 3, width, width).clone(),
        "vertical-gradient": vertical.expand(1, 3, width, width).clone(),
        "seeded-noise": torch.rand(
            1, 3, width, width, generator=generator
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yolox_source", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--precision", choices=("default", "float32"), default="default"
    )
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("refusing to overwrite output directory")
    if not (args.yolox_source / "yolox").is_dir() or not args.checkpoint.is_file():
        parser.error("YOLOX source or checkpoint is missing")
    args.output_dir.mkdir(parents=True)

    sys.path.insert(0, str(args.yolox_source))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import coremltools as ct
    import numpy as np
    import torch
    from aegis360.detector_equivalence import compare_detector_outputs
    from aegis360.yolox_decode import decode_yolox, detection_document
    from yolox.exp import get_exp

    exp_path = args.yolox_source / "exps/default/yolox_tiny.py"
    exp = get_exp(str(exp_path), None)
    model = exp.get_model().eval()
    checkpoint = torch.load(
        args.checkpoint, map_location="cpu", weights_only=False
    )
    model.load_state_dict(checkpoint["model"], strict=True)
    model.head.decode_in_inference = False
    generated = fixtures(torch)
    fixture = generated["zeros"]
    with torch.no_grad():
        reference = model(fixture).detach().cpu().numpy()

    traced = torch.jit.trace(model, fixture, strict=True)
    with torch.no_grad():
        traced_reference = traced(fixture).detach().cpu().numpy()
    if not np.array_equal(reference, traced_reference):
        raise RuntimeError("TorchScript trace changed raw reference output")

    conversion_options = {}
    if args.precision == "float32":
        conversion_options["compute_precision"] = ct.precision.FLOAT32
    converted = ct.convert(
        traced,
        inputs=[ct.TensorType(name="image", shape=fixture.shape)],
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.macOS15,
        **conversion_options,
    )
    package = args.output_dir / "YOLOX-Tiny-0.1.1rc0.mlpackage"
    converted.save(package)
    reports = []
    for name, fixture_input in generated.items():
        with torch.no_grad():
            reference = model(fixture_input).detach().cpu().numpy()
        prediction = converted.predict({"image": fixture_input.numpy()})
        if len(prediction) != 1:
            raise RuntimeError("converted model returned unexpected output count")
        candidate = np.asarray(next(iter(prediction.values())))
        reference_path = args.output_dir / f"reference-{name}.json"
        candidate_path = args.output_dir / f"coreml-{name}.json"
        reference_detections = detection_document(decode_yolox(reference[0]))
        candidate_detections = detection_document(decode_yolox(candidate[0]))
        write_output(
            reference_path, reference, reference.shape, reference_detections
        )
        write_output(
            candidate_path, candidate, candidate.shape, candidate_detections
        )
        report = compare_detector_outputs(
            json.loads(reference_path.read_text()),
            json.loads(candidate_path.read_text()),
        )
        report["fixture"] = name
        (args.output_dir / f"equivalence-{name}.json").write_text(
            json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n"
        )
        reports.append(report)
    summary = {
        "schema_version": "aegis360.yolox-coreml-generated-gate.v1",
        "passed": all(report["passed"] for report in reports),
        "torch_version": torch.__version__,
        "coremltools_version": ct.__version__,
        "conversion_precision": args.precision,
        "fixtures": [{
            "name": report["fixture"],
            "passed": report["passed"],
            "maximum_absolute_error": report["raw"]["maximum_absolute_error"],
            "mean_absolute_error": report["raw"]["mean_absolute_error"],
            "top_index_agreements": report["raw"]["top_index_agreements"],
            "decoded_detection_count": len(reference_detections),
            "decoded_passed": report["decoded"]["passed"],
        } for report in reports],
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"passed={str(summary['passed']).lower()} fixtures={len(reports)} "
        f"shape={tuple(reference.shape)} package={package}"
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
