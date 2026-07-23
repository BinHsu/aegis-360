"""Replaceable perception boundary for spherical candidate evidence.

The contract is deliberately model-agnostic.  Adapters report observations
and normalized evidence; an explicit, separate scoring configuration converts
that evidence into the greedy baseline's input.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol, runtime_checkable

from .greedy_planner import CandidateObservation, Observation, ScoreComponent


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field} must be nonempty")


@dataclass(frozen=True)
class FrameSample:
    """Privacy-safe metadata for one decoded analysis sample.

    ``source_id`` is job-scoped and must not be an absolute source path.
    Pixel storage is intentionally outside this core contract so each backend
    can consume the bounded buffer representation appropriate to its runtime.
    """

    source_id: str
    timestamp: float
    frame_index: int
    width: int
    height: int
    projection: str = "equirectangular"

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if self.source_id.startswith(("/", "~")):
            raise ValueError("source_id must be privacy-safe, not a path")
        if not math.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("timestamp must be finite and nonnegative")
        if self.frame_index < 0:
            raise ValueError("frame_index must be nonnegative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("sample dimensions must be positive")
        _require_text(self.projection, "projection")


@dataclass(frozen=True)
class AdapterProvenance:
    """Identity needed to reproduce evidence without vendor-specific objects."""

    adapter_id: str
    adapter_version: str
    backend_id: str
    projection_strategy: str
    weights_sha256: str | None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.adapter_id, "adapter_id"),
            (self.adapter_version, "adapter_version"),
            (self.backend_id, "backend_id"),
            (self.projection_strategy, "projection_strategy"),
        ):
            _require_text(value, field)
        if self.weights_sha256 is not None:
            digest = self.weights_sha256.lower()
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("weights_sha256 must be a 64-character hexadecimal digest")

    @property
    def label(self) -> str:
        return f"{self.adapter_id}@{self.adapter_version}/{self.backend_id}:{self.projection_strategy}"


@dataclass(frozen=True)
class SignalEvidence:
    """One backend-independent interest signal.

    Missing signals use ``normalized=None`` plus a reason.  Present normalized
    values are constrained to [0, 1]; weights do not belong here.
    """

    name: str
    raw: float | None
    normalized: float | None
    provenance: str
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "signal name")
        _require_text(self.provenance, "signal provenance")
        if self.raw is not None and not math.isfinite(self.raw):
            raise ValueError("raw signal values must be finite")
        if self.normalized is None:
            if self.raw is not None:
                raise ValueError("missing normalized evidence cannot have a raw value")
            if self.missing_reason is None or not self.missing_reason.strip():
                raise ValueError("missing evidence requires a reason")
        else:
            if not math.isfinite(self.normalized) or not 0.0 <= self.normalized <= 1.0:
                raise ValueError("normalized evidence must be finite and in [0, 1]")
            if self.missing_reason is not None:
                raise ValueError("present evidence cannot have a missing reason")


@dataclass(frozen=True)
class SphericalCandidateEvidence:
    """Candidate or track evidence expressed in spherical coordinates."""

    candidate_id: str
    track_id: str | None
    yaw: float
    pitch: float
    h_fov: float
    candidate_type: str
    signals: tuple[SignalEvidence, ...]
    observation_provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        if self.track_id is not None:
            _require_text(self.track_id, "track_id")
        if not all(math.isfinite(value) for value in (self.yaw, self.pitch, self.h_fov)):
            raise ValueError("candidate geometry must be finite")
        if not -math.pi <= self.yaw <= math.pi:
            raise ValueError("yaw must use the canonical [-pi, pi] range")
        if not -math.pi / 2 <= self.pitch <= math.pi / 2:
            raise ValueError("pitch must remain between the poles")
        if not 0 < self.h_fov < math.pi:
            raise ValueError("horizontal FOV must be between zero and pi")
        _require_text(self.candidate_type, "candidate_type")
        names = [signal.name for signal in self.signals]
        if len(names) != len(set(names)):
            raise ValueError("signal names must be unique per candidate")
        if not self.observation_provenance:
            raise ValueError("observation provenance must be retained")
        for item in self.observation_provenance:
            _require_text(item, "observation provenance")


@dataclass(frozen=True)
class PerceptionResult:
    sample: FrameSample
    adapter: AdapterProvenance
    candidates: tuple[SphericalCandidateEvidence, ...]

    def __post_init__(self) -> None:
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique per sample")


@runtime_checkable
class PerceptionAdapter(Protocol):
    """Minimal replaceable detector/tracker task adapter."""

    @property
    def provenance(self) -> AdapterProvenance:
        ...

    def analyze(self, sample: FrameSample) -> PerceptionResult:
        ...


@dataclass(frozen=True)
class ScoringConfig:
    """Editorial weights applied after perception."""

    weights: tuple[tuple[str, float], ...]
    missing_normalized: float = 0.0

    def __post_init__(self) -> None:
        names = [name for name, _ in self.weights]
        if any(not name.strip() for name in names) or len(names) != len(set(names)):
            raise ValueError("scoring signal names must be nonempty and unique")
        if not all(math.isfinite(weight) for _, weight in self.weights):
            raise ValueError("scoring weights must be finite")
        if not math.isfinite(self.missing_normalized) or not 0 <= self.missing_normalized <= 1:
            raise ValueError("missing_normalized must be in [0, 1]")


def to_greedy_observation(result: PerceptionResult, scoring: ScoringConfig) -> Observation:
    """Convert evidence to planner input without embedding scoring in adapters."""

    converted: list[CandidateObservation] = []
    for candidate in result.candidates:
        signals = {signal.name: signal for signal in candidate.signals}
        components: list[ScoreComponent] = []
        for name, weight in scoring.weights:
            signal = signals.get(name)
            if signal is None:
                raw = None
                normalized = scoring.missing_normalized
                provenance = f"{result.adapter.label};missing:not_reported"
            elif signal.normalized is None:
                raw = None
                normalized = scoring.missing_normalized
                provenance = (
                    f"{signal.provenance};missing:{signal.missing_reason}"
                )
            else:
                raw = signal.raw
                normalized = signal.normalized
                provenance = signal.provenance
            components.append(ScoreComponent(name, raw, normalized, weight, provenance))

        # Signals not selected by the scorer are intentionally not planner
        # components.  They remain available in the cacheable PerceptionResult.
        converted.append(
            CandidateObservation(
                candidate_id=candidate.candidate_id,
                yaw=candidate.yaw,
                pitch=candidate.pitch,
                h_fov=candidate.h_fov,
                candidate_type=candidate.candidate_type,
                components=tuple(components),
            )
        )
    return Observation(result.sample.timestamp, tuple(converted))
