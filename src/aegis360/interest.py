"""Explainable editorial-interest evidence for temporal candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .candidate_sequence import CandidateFrame, TemporalCandidate
from .geometry import spherical_distance
from .perception import SignalEvidence


INTEREST_SIGNAL_NAMES = (
    "presence",
    "persistence",
    "composition",
    "forward_prior",
)


@dataclass(frozen=True)
class InterestConfig:
    persistence_frames: int = 5
    composition_pitch_limit: float = math.radians(45.0)
    forward_falloff: float = math.radians(90.0)
    forward_yaw: float = 0.0
    forward_pitch: float = 0.0

    def __post_init__(self) -> None:
        if self.persistence_frames <= 0:
            raise ValueError("persistence_frames must be positive")
        if not math.isfinite(self.composition_pitch_limit) or not 0 < self.composition_pitch_limit <= math.pi / 2:
            raise ValueError("composition_pitch_limit must be in (0, pi/2]")
        if not math.isfinite(self.forward_falloff) or not 0 < self.forward_falloff <= math.pi:
            raise ValueError("forward_falloff must be in (0, pi]")


@dataclass(frozen=True)
class InterestedCandidate:
    candidate: TemporalCandidate
    signals: tuple[SignalEvidence, ...]


@dataclass(frozen=True)
class InterestFrame:
    timestamp: float
    frame_index: int
    candidates: tuple[InterestedCandidate, ...]


def candidate_interest(
    candidate: TemporalCandidate,
    config: InterestConfig = InterestConfig(),
) -> tuple[SignalEvidence, ...]:
    """Return named evidence; detector confidence is deliberately not accepted."""

    # The forward context is a safe camera fallback, not a detected entity.
    # Giving it presence/persistence would let an always-available synthetic
    # candidate dominate real observations by construction.
    is_context = candidate.candidate_type == "context"
    presence = 0.0 if is_context else (1.0 if candidate.observed else 0.0)
    persistence = (
        0.0
        if is_context or not candidate.editorial_persistence_valid
        else min(1.0, candidate.observed_frames / config.persistence_frames)
    )
    composition = max(
        0.0, 1.0 - abs(candidate.pitch) / config.composition_pitch_limit
    )
    forward_distance = spherical_distance(
        (candidate.yaw, candidate.pitch),
        (config.forward_yaw, config.forward_pitch),
    )
    forward_prior = max(0.0, 1.0 - forward_distance / config.forward_falloff)
    provenance = "aegis360.interest:v1"
    return (
        SignalEvidence("presence", presence, presence, provenance),
        SignalEvidence(
            "persistence",
            (
                float(candidate.observed_frames)
                if candidate.editorial_persistence_valid
                else 0.0
            ),
            persistence,
            (
                f"{provenance};normalizer:{config.persistence_frames}-frames;"
                f"association:{candidate.association_provenance.value}"
            ),
        ),
        SignalEvidence(
            "composition",
            abs(candidate.pitch),
            composition,
            f"{provenance};center-pitch",
        ),
        SignalEvidence(
            "forward_prior",
            forward_distance,
            forward_prior,
            f"{provenance};great-circle-forward",
        ),
    )


def evaluate_interest(
    frames: tuple[CandidateFrame, ...],
    config: InterestConfig = InterestConfig(),
) -> tuple[InterestFrame, ...]:
    return tuple(
        InterestFrame(
            frame.timestamp,
            frame.frame_index,
            tuple(
                InterestedCandidate(candidate, candidate_interest(candidate, config))
                for candidate in frame.candidates
            ),
        )
        for frame in frames
    )
