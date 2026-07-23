#!/usr/bin/env python3
"""Ingest a Vision fixed batch and write a privacy-safe spherical-dedup report."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.greedy_planner import (  # noqa: E402
    GreedyConfig,
    dumps_trace,
    plan_greedy_with_hysteresis,
)
from aegis360.perception import ScoringConfig, to_greedy_observation  # noqa: E402
from aegis360.spherical_dedup import (  # noqa: E402
    deduplicate_spherical_candidates,
    vision_gate_json_to_perception,
)

OBSERVATION_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")


def _kind_counts(candidates) -> dict[str, int]:
    return dict(sorted(Counter(item.candidate_type for item in candidates).items()))


def build_report(evidence_paths: list[Path]) -> tuple[dict[str, object], list]:
    if not evidence_paths:
        raise ValueError("input batch contains no per-sample Vision evidence")

    samples: list[dict[str, object]] = []
    observations = []
    source_ids: set[str] = set()
    adapter_labels: set[str] = set()
    raw_total = 0
    cluster_total = 0
    raw_kinds: Counter[str] = Counter()
    dedup_kinds: Counter[str] = Counter()

    for evidence_path in evidence_paths:
        results = vision_gate_json_to_perception(
            evidence_path.read_text(encoding="utf-8"), width=1, height=1
        )
        if len(results) != 1:
            raise ValueError(
                f"{evidence_path.parent.name}: expected exactly one grouped sample"
            )
        raw = results[0]
        for candidate in raw.candidates:
            if not OBSERVATION_ID.fullmatch(candidate.candidate_id):
                raise ValueError("candidate IDs must be privacy-safe tokens")
        deduped = deduplicate_spherical_candidates(raw)
        source_ids.add(raw.sample.source_id)
        adapter_labels.add(raw.adapter.label)
        raw_total += len(raw.candidates)
        cluster_total += len(deduped.clusters)
        raw_kinds.update(item.candidate_type for item in raw.candidates)
        dedup_kinds.update(item.candidate_type for item in deduped.result.candidates)
        samples.append(
            {
                "timestamp_seconds": raw.sample.timestamp,
                "raw_candidate_count": len(raw.candidates),
                "cluster_count": len(deduped.clusters),
                "raw_kind_counts": _kind_counts(raw.candidates),
                "deduplicated_kind_counts": _kind_counts(
                    deduped.result.candidates
                ),
                "clusters": [
                    {
                        "cluster_id": cluster.candidate.candidate_id,
                        "kind": cluster.candidate.candidate_type,
                        "member_count": len(cluster.members),
                        "member_ids": sorted(
                            member.candidate_id for member in cluster.members
                        ),
                    }
                    for cluster in deduped.clusters
                ],
            }
        )
        # Zero-weight missing evidence is intentional: this checks only the
        # perception-to-planner contract and never treats confidence as interest.
        observations.append(
            to_greedy_observation(
                deduped.result,
                ScoringConfig((("neutral_contract_wiring", 0.0),)),
            )
        )

    if len(source_ids) != 1:
        raise ValueError("batch evidence must contain exactly one privacy-safe source ID")
    if len(adapter_labels) != 1:
        raise ValueError("batch evidence must contain exactly one adapter provenance")
    samples.sort(key=lambda item: item["timestamp_seconds"])
    observations.sort(key=lambda item: item.timestamp)
    timestamps = [item["timestamp_seconds"] for item in samples]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("batch evidence contains duplicate timestamps")

    report = {
        "schema_version": "aegis360.vision-spherical-dedup-report.v1",
        "source_id": next(iter(source_ids)),
        "provenance_summary": {
            "adapter": next(iter(adapter_labels)),
            "input_schema": "Apple Vision frame gate v1",
            "deduplicator": "aegis360.spherical_dedup.geometric-connected-components",
            "confidence_used_for_deduplication": False,
        },
        "sample_count": len(samples),
        "raw_candidate_count": raw_total,
        "cluster_count": cluster_total,
        "raw_kind_counts": dict(sorted(raw_kinds.items())),
        "deduplicated_kind_counts": dict(sorted(dedup_kinds.items())),
        "samples": samples,
        "limitations": [
            "Candidate and cluster counts are unreviewed observations, not quality, precision, recall, tracking, or editorial-value measurements.",
            "Geometric connected components can transitively merge a chain of nearby same-kind candidates.",
            "Detector confidence is retained only in the input evidence contract and is not used for deduplication or editorial scoring.",
            "Cluster member IDs are observation identifiers, not persistent identities across timestamps.",
        ],
    }
    return report, observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_batch_dir", type=Path)
    parser.add_argument("output_report", type=Path)
    parser.add_argument("--greedy-trace", type=Path)
    args = parser.parse_args()

    if not args.input_batch_dir.is_dir():
        parser.error("input batch directory does not exist")
    if (
        args.greedy_trace is not None
        and args.output_report.resolve() == args.greedy_trace.resolve()
    ):
        parser.error("report and greedy trace outputs must be different files")
    for output in (args.output_report, args.greedy_trace):
        if output is not None and output.exists():
            parser.error(f"refusing to overwrite output: {output}")
    evidence_paths = sorted(
        args.input_batch_dir.glob("sample-*/vision-frame-gate.json")
    )
    report, observations = build_report(evidence_paths)

    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(
        json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.greedy_trace is not None:
        trace = plan_greedy_with_hysteresis(
            observations,
            GreedyConfig(
                minimum_dwell_seconds=0.0,
                switch_margin=0.0,
                challenger_hold_seconds=0.0,
            ),
        )
        trace["scoring_policy"] = {
            "name": "neutral_contract_wiring",
            "candidate_utility": 0.0,
            "detector_confidence_used": False,
            "selection_semantics": "deterministic candidate-ID tie-break only",
        }
        trace["limitations"] = [
            "This trace proves contract wiring only and is not an auto-director quality result.",
            "No editorial interest signal is present; every candidate has zero utility.",
        ]
        args.greedy_trace.parent.mkdir(parents=True, exist_ok=True)
        args.greedy_trace.write_text(dumps_trace(trace), encoding="utf-8")

    print(args.output_report)
    if args.greedy_trace is not None:
        print(args.greedy_trace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
