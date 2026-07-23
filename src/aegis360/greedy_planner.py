"""Explainable greedy-with-hysteresis planner baseline.

This module intentionally consumes already-normalized candidate evidence.  It
does not perform perception and has no third-party dependencies.  The planner
is a behavioral baseline, not the repository's eventual global planner.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Iterable

from .geometry import spherical_distance


@dataclass(frozen=True)
class ScoreComponent:
    """One inspectable contribution to a candidate's utility."""

    name: str
    raw: float | None
    normalized: float
    weight: float
    provenance: str

    @property
    def contribution(self) -> float:
        return self.normalized * self.weight


@dataclass(frozen=True)
class CandidateObservation:
    """A bounded candidate view at one analysis timestamp."""

    candidate_id: str
    yaw: float
    pitch: float
    h_fov: float
    candidate_type: str
    components: tuple[ScoreComponent, ...]

    @property
    def utility(self) -> float:
        return sum(component.contribution for component in self.components)


@dataclass(frozen=True)
class Observation:
    timestamp: float
    candidates: tuple[CandidateObservation, ...]


@dataclass(frozen=True)
class GreedyConfig:
    minimum_dwell_seconds: float = 2.0
    switch_margin: float = 0.1
    challenger_hold_seconds: float = 0.5


def _validate(observations: Iterable[Observation], config: GreedyConfig) -> tuple[Observation, ...]:
    items = tuple(observations)
    config_values = (
        config.minimum_dwell_seconds,
        config.switch_margin,
        config.challenger_hold_seconds,
    )
    if not all(math.isfinite(value) and value >= 0.0 for value in config_values):
        raise ValueError("planner thresholds must be finite and nonnegative")

    previous_time = -math.inf
    for observation in items:
        if not math.isfinite(observation.timestamp) or observation.timestamp < 0:
            raise ValueError("observation timestamps must be finite and nonnegative")
        if observation.timestamp <= previous_time:
            raise ValueError("observation timestamps must be strictly increasing")
        if not observation.candidates:
            raise ValueError("each observation requires at least one candidate")
        ids: set[str] = set()
        for candidate in observation.candidates:
            if not candidate.candidate_id or candidate.candidate_id in ids:
                raise ValueError("candidate IDs must be nonempty and unique per observation")
            ids.add(candidate.candidate_id)
            values = (candidate.yaw, candidate.pitch, candidate.h_fov, candidate.utility)
            if not all(math.isfinite(value) for value in values):
                raise ValueError("candidate geometry and utility must be finite")
            if not -math.pi / 2 <= candidate.pitch <= math.pi / 2:
                raise ValueError("candidate pitch must remain between the poles")
            if not 0 < candidate.h_fov < math.pi:
                raise ValueError("candidate horizontal FOV must be between zero and pi")
            component_names: set[str] = set()
            for component in candidate.components:
                if not component.name or component.name in component_names:
                    raise ValueError("score component names must be nonempty and unique")
                component_names.add(component.name)
                component_values = (component.normalized, component.weight)
                if component.raw is not None:
                    component_values += (component.raw,)
                if not all(math.isfinite(value) for value in component_values):
                    raise ValueError("score components must contain finite values")
                if not 0.0 <= component.normalized <= 1.0:
                    raise ValueError("normalized score components must be in [0, 1]")
        previous_time = observation.timestamp
    return items


def _rank(candidates: Iterable[CandidateObservation]) -> list[CandidateObservation]:
    """Rank by utility and then stable ephemeral ID for deterministic ties."""

    return sorted(candidates, key=lambda candidate: (-candidate.utility, candidate.candidate_id))


def _candidate_trace(candidate: CandidateObservation) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "yaw_radians": candidate.yaw,
        "pitch_radians": candidate.pitch,
        "h_fov_radians": candidate.h_fov,
        "utility": candidate.utility,
        "score_components": [
            {
                "name": component.name,
                "raw": component.raw,
                "normalized": component.normalized,
                "weight": component.weight,
                "contribution": component.contribution,
                "provenance": component.provenance,
                "missing": component.raw is None,
            }
            for component in sorted(candidate.components, key=lambda item: item.name)
        ],
    }


def plan_greedy_with_hysteresis(
    observations: Iterable[Observation], config: GreedyConfig = GreedyConfig()
) -> dict[str, object]:
    """Select one view per observation and return a JSON-compatible trace.

    A present incumbent is retained until minimum dwell has elapsed.  After
    that, a challenger must exceed the incumbent by ``switch_margin`` and stay
    the best challenger for ``challenger_hold_seconds``.  If the incumbent is
    absent, the deterministic best available candidate is selected immediately.
    """

    items = _validate(observations, config)
    decisions: list[dict[str, object]] = []
    incumbent_id: str | None = None
    incumbent_since = 0.0
    previous_selected: CandidateObservation | None = None
    challenger_id: str | None = None
    challenger_since = 0.0

    for observation in items:
        ranked = _rank(observation.candidates)
        by_id = {candidate.candidate_id: candidate for candidate in observation.candidates}
        selected: CandidateObservation
        switched = False
        fallback = False
        reason: str

        if incumbent_id is None:
            selected = ranked[0]
            incumbent_since = observation.timestamp
            reason = "initial_best"
        elif incumbent_id not in by_id:
            selected = ranked[0]
            incumbent_since = observation.timestamp
            switched = selected.candidate_id != incumbent_id
            fallback = True
            reason = "incumbent_missing_fallback"
            challenger_id = None
        else:
            incumbent = by_id[incumbent_id]
            challenger = ranked[0]
            dwell = observation.timestamp - incumbent_since
            if challenger.candidate_id == incumbent_id:
                selected = incumbent
                reason = "incumbent_best"
                challenger_id = None
            elif dwell < config.minimum_dwell_seconds:
                selected = incumbent
                reason = "minimum_dwell"
                challenger_id = None
            elif challenger.utility < incumbent.utility + config.switch_margin:
                selected = incumbent
                reason = "switch_margin"
                challenger_id = None
            else:
                if challenger_id != challenger.candidate_id:
                    challenger_id = challenger.candidate_id
                    challenger_since = observation.timestamp
                held = observation.timestamp - challenger_since
                if held < config.challenger_hold_seconds:
                    selected = incumbent
                    reason = "challenger_hysteresis"
                else:
                    selected = challenger
                    incumbent_since = observation.timestamp
                    switched = True
                    reason = "sustained_challenger"
                    challenger_id = None

        transition = None
        if previous_selected is not None:
            transition = {
                "from_candidate_id": previous_selected.candidate_id,
                "to_candidate_id": selected.candidate_id,
                "angular_distance_radians": spherical_distance(
                    (previous_selected.yaw, previous_selected.pitch),
                    (selected.yaw, selected.pitch),
                ),
                "switched": switched,
            }
        incumbent_id = selected.candidate_id
        decisions.append(
            {
                "timestamp": observation.timestamp,
                "candidates": [_candidate_trace(candidate) for candidate in ranked],
                "selected_candidate_id": selected.candidate_id,
                "reason": reason,
                "fallback": fallback,
                "transition": transition,
            }
        )
        previous_selected = selected

    return {
        "schema_version": "aegis360.greedy-baseline.v1",
        "planner": "greedy_with_hysteresis",
        "config": {
            "minimum_dwell_seconds": config.minimum_dwell_seconds,
            "switch_margin": config.switch_margin,
            "challenger_hold_seconds": config.challenger_hold_seconds,
            "tie_break": "candidate_id_ascending",
        },
        "decisions": decisions,
        "warnings": ["incumbent candidate missing; deterministic fallback used"]
        if any(decision["fallback"] for decision in decisions)
        else [],
    }


def dumps_trace(trace: dict[str, object]) -> str:
    """Serialize a trace deterministically and reject non-finite JSON values."""

    return json.dumps(trace, allow_nan=False, indent=2, sort_keys=True) + "\n"
