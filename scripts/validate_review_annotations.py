#!/usr/bin/env python3
"""Validate a manual perception review JSON document."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.review_annotations import validate_review_annotation  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} ANNOTATION_JSON")
    validate_review_annotation(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"valid: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
