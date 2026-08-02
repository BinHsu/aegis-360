"""Fail-closed detector-only semantic tracklet lifecycle diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .geometry import spherical_distance
from .perception import PerceptionResult, SphericalCandidateEvidence


@dataclass(frozen=True)
class SemanticTrackletPolicy:
    maximum_distance_radians: float = math.radians(12)
    confirmations_required: int = 2
    minimum_confirmation_span_seconds: float = .25
    missing_grace_samples: int = 2

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.maximum_distance_radians)
            or not 0 < self.maximum_distance_radians < math.pi
            or isinstance(self.confirmations_required, bool)
            or not isinstance(self.confirmations_required, int)
            or self.confirmations_required < 2
            or not math.isfinite(self.minimum_confirmation_span_seconds)
            or self.minimum_confirmation_span_seconds <= 0
            or isinstance(self.missing_grace_samples, bool)
            or not isinstance(self.missing_grace_samples, int)
            or self.missing_grace_samples < 0
        ):
            raise ValueError("semantic tracklet policy is invalid")


@dataclass
class _Hypothesis:
    hypothesis_id: str
    class_name: str
    yaw: float
    pitch: float
    first_timestamp: float
    confirmations: int = 1
    track_id: str | None = None
    observed_samples: int = 0
    missing_samples: int = 0


def build_semantic_tracklet_diagnostic(
    results: Iterable[PerceptionResult],
    policy: SemanticTrackletPolicy = SemanticTrackletPolicy(),
) -> dict[str, object]:
    """Acquire only mutual-unique geometry chains; never assert identity."""

    sequence = tuple(results)
    previous_timestamp = -math.inf
    hypotheses: dict[str, _Hypothesis] = {}
    next_hypothesis = 1
    next_track = 1
    acquired = []
    terminated = []
    samples = []
    for result in sequence:
        timestamp = result.sample.timestamp
        if timestamp <= previous_timestamp:
            raise ValueError("semantic timestamps must increase")
        previous_timestamp = timestamp
        observations = tuple(sorted(
            result.candidates,
            key=lambda item: (
                item.candidate_type, item.yaw, item.pitch, item.candidate_id
            ),
        ))
        compatible_by_hypothesis: dict[str, list[int]] = {
            key: [] for key in hypotheses
        }
        compatible_by_observation: list[list[str]] = [
            [] for _ in observations
        ]
        for hypothesis_id, hypothesis in hypotheses.items():
            for index, observation in enumerate(observations):
                if (
                    hypothesis.class_name == observation.candidate_type
                    and spherical_distance(
                        (hypothesis.yaw, hypothesis.pitch),
                        (observation.yaw, observation.pitch),
                    ) <= policy.maximum_distance_radians
                ):
                    compatible_by_hypothesis[hypothesis_id].append(index)
                    compatible_by_observation[index].append(hypothesis_id)

        matches = {}
        for hypothesis_id, indices in compatible_by_hypothesis.items():
            if len(indices) == 1 and len(compatible_by_observation[indices[0]]) == 1:
                matches[hypothesis_id] = indices[0]
        ambiguous_hypotheses = sum(
            len(indices) > 1 for indices in compatible_by_hypothesis.values()
        )
        ambiguous_observations = sum(
            len(ids) > 1 for ids in compatible_by_observation
        )

        matched_observations = set(matches.values())
        for hypothesis_id in tuple(sorted(hypotheses)):
            hypothesis = hypotheses[hypothesis_id]
            index = matches.get(hypothesis_id)
            if index is None:
                if hypothesis.track_id is None:
                    del hypotheses[hypothesis_id]
                    continue
                hypothesis.missing_samples += 1
                if hypothesis.missing_samples > policy.missing_grace_samples:
                    terminated.append({
                        "track_id": hypothesis.track_id,
                        "terminated_at": timestamp,
                        "reason": "missing_or_ambiguous_timeout",
                    })
                    del hypotheses[hypothesis_id]
                continue
            observation = observations[index]
            hypothesis.yaw = observation.yaw
            hypothesis.pitch = observation.pitch
            hypothesis.missing_samples = 0
            hypothesis.confirmations += 1
            hypothesis.observed_samples += 1
            if (
                hypothesis.track_id is None
                and hypothesis.confirmations >= policy.confirmations_required
                and timestamp - hypothesis.first_timestamp
                >= policy.minimum_confirmation_span_seconds
            ):
                hypothesis.track_id = f"semantic-track:{next_track:06d}"
                next_track += 1
                acquired.append({
                    "track_id": hypothesis.track_id,
                    "acquired_at": timestamp,
                    "class_name": hypothesis.class_name,
                    "identity_verified": False,
                    "editorial_persistence_allowed": False,
                })

        for index, observation in enumerate(observations):
            if index in matched_observations or compatible_by_observation[index]:
                continue
            hypothesis_id = f"proposal:{next_hypothesis:06d}"
            next_hypothesis += 1
            hypotheses[hypothesis_id] = _Hypothesis(
                hypothesis_id, observation.candidate_type,
                observation.yaw, observation.pitch, timestamp,
                observed_samples=1,
            )

        active_tracks = sorted(
            (
                {
                    "track_id": hypothesis.track_id,
                    "class_name": hypothesis.class_name,
                    "yaw_radians": hypothesis.yaw,
                    "pitch_radians": hypothesis.pitch,
                    "observed_samples": hypothesis.observed_samples,
                    "missing_samples": hypothesis.missing_samples,
                    "identity_verified": False,
                    "editorial_persistence_allowed": False,
                }
                for hypothesis in hypotheses.values()
                if hypothesis.track_id is not None
            ),
            key=lambda row: row["track_id"],
        )
        samples.append({
            "timestamp_seconds": timestamp,
            "observation_count": len(observations),
            "ambiguous_hypothesis_count": ambiguous_hypotheses,
            "ambiguous_observation_count": ambiguous_observations,
            "active_tracks": active_tracks,
        })

    return {
        "schema_version": "aegis360.semantic-tracklet-diagnostic.v1",
        "policy": {
            "maximum_distance_radians": policy.maximum_distance_radians,
            "confirmations_required": policy.confirmations_required,
            "minimum_confirmation_span_seconds": policy.minimum_confirmation_span_seconds,
            "missing_grace_samples": policy.missing_grace_samples,
            "mutual_unique_compatibility_required": True,
            "uses_detector_confidence": False,
        },
        "acquisitions": acquired,
        "terminations": terminated,
        "samples": samples,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitation": (
            "Detector class and mutual-unique geometry create operational "
            "tracklets, not verified identity or editorial persistence."
        ),
    }
