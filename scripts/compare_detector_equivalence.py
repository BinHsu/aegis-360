#!/usr/bin/env python3
"""Compare reference and converted detector JSON without loading a model."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_equivalence import compare_detector_outputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_json", type=Path)
    parser.add_argument("candidate_json", type=Path)
    parser.add_argument("report_json", type=Path)
    args = parser.parse_args()
    if args.report_json.exists():
        parser.error("refusing to overwrite report")
    report = compare_detector_outputs(
        json.loads(args.reference_json.read_text()),
        json.loads(args.candidate_json.read_text()),
    )
    args.report_json.write_text(
        json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n"
    )
    print(f"passed={str(report['passed']).lower()} report={args.report_json}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
