#!/usr/bin/env python3
"""Summarize bounded scene-context outcomes without making accuracy claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.scene_context import validate_scene_context  # noqa: E402


OUTCOMES = {"group_selected", "person_selected", "context_selected", "abstained"}


def load_expectations(path: Path) -> dict[tuple[str, str], str]:
    root = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(root, dict) or set(root) != {"schema_version", "cases"}:
        raise ValueError("expectation manifest fields must match the closed schema")
    if root["schema_version"] != "aegis360.local-context-gate-expectations.v1":
        raise ValueError("unsupported expectation manifest schema")
    if not isinstance(root["cases"], list) or not root["cases"]:
        raise ValueError("expectation manifest requires cases")
    expectations: dict[tuple[str, str], str] = {}
    for case in root["cases"]:
        if not isinstance(case, dict) or set(case) != {
            "source_id", "window_id", "expected_outcome",
        }:
            raise ValueError("expectation case fields must match the closed schema")
        key = (case["source_id"], case["window_id"])
        if not all(isinstance(value, str) and value for value in key):
            raise ValueError("expectation case IDs must be nonempty strings")
        if case["expected_outcome"] not in OUTCOMES:
            raise ValueError("expected outcome is unsupported")
        if key in expectations:
            raise ValueError("expectation case keys must be unique")
        expectations[key] = case["expected_outcome"]
    return expectations


def observed_outcome(document: dict[str, object]) -> str:
    decision = validate_scene_context(document)
    if decision.selected_candidate_id is None:
        return "abstained"
    candidate = next(
        item for item in decision.candidates
        if item.candidate_id == decision.selected_candidate_id
    )
    return f"{candidate.candidate_type}_selected"


def summarize(expectation_path: Path, context_paths: list[Path]) -> dict[str, object]:
    expectations = load_expectations(expectation_path)
    observed: dict[tuple[str, str], str] = {}
    for path in context_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        outcome = observed_outcome(document)
        window = document.get("window")
        if not isinstance(window, dict):
            raise ValueError("scene context window is missing")
        key = (window.get("source_id"), window.get("window_id"))
        if key in observed:
            raise ValueError("scene context case keys must be unique")
        observed[key] = outcome
    if set(observed) != set(expectations):
        raise ValueError("observed scene-context cases must exactly match expectations")
    cases = [
        {
            "source_id": key[0], "window_id": key[1],
            "expected_outcome": expectations[key],
            "observed_outcome": observed[key],
            "passed": expectations[key] == observed[key],
        }
        for key in sorted(expectations)
    ]
    counts = {
        outcome: sum(case["observed_outcome"] == outcome for case in cases)
        for outcome in sorted(OUTCOMES)
    }
    return {
        "schema_version": "aegis360.local-context-gate-summary.v1",
        "case_count": len(cases),
        "expectations_met": all(case["passed"] for case in cases),
        "observed_outcome_counts": counts,
        "cases": cases,
        "excluded_from_scoring": ["context_class", "evidence_flags"],
        "limitations": [
            "case outcomes are bounded gate evidence, not an accuracy estimate",
            "expectations require independent human screening",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expectations", type=Path)
    parser.add_argument("contexts", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        summary = summarize(args.expectations, args.contexts)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
