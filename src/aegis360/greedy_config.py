"""Versioned configuration contract for the first greedy vertical slice."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib

from .greedy_planner import GreedyConfig
from .framing import FramingSafetyConfig
from .interest import INTEREST_SIGNAL_NAMES
from .perception import ScoringConfig


SCHEMA_VERSION = "aegis360.greedy-config.v1"
_ROOT_KEYS = frozenset(("schema_version", "weights", "hysteresis", "camera"))
_HYSTERESIS_KEYS = frozenset(
    ("minimum_dwell_seconds", "switch_margin", "challenger_hold_seconds")
)
_CAMERA_KEYS = frozenset((
    "min_angular_change_degrees",
    "minimum_horizontal_fov_degrees",
    "candidate_extent_padding_degrees",
    "maximum_zoom_in_change_degrees",
))


@dataclass(frozen=True)
class GreedySliceConfig:
    """Validated scoring, switching, and sparse-camera-keyframe settings."""

    schema_version: str
    scoring: ScoringConfig
    planner: GreedyConfig
    camera_min_angular_change: float
    framing_safety: FramingSafetyConfig

    def camera_change_is_material(self, angular_distance: float) -> bool:
        """Return whether a camera change should produce a sparse keyframe."""

        if not math.isfinite(angular_distance) or angular_distance < 0:
            raise ValueError("angular_distance must be finite and nonnegative")
        return angular_distance >= self.camera_min_angular_change

    def trace_config(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "weights": dict(self.scoring.weights),
            "hysteresis": {
                "minimum_dwell_seconds": self.planner.minimum_dwell_seconds,
                "switch_margin": self.planner.switch_margin,
                "challenger_hold_seconds": self.planner.challenger_hold_seconds,
            },
            "camera": {
                "min_angular_change_degrees": math.degrees(
                    self.camera_min_angular_change
                ),
                "purpose": "sparse_keyframe_threshold",
                "framing_safety": {
                    "minimum_horizontal_fov_degrees": math.degrees(
                        self.framing_safety.minimum_h_fov
                    ),
                    "candidate_extent_padding_degrees": math.degrees(
                        self.framing_safety.candidate_extent_padding
                    ),
                    "maximum_zoom_in_change_degrees": math.degrees(
                        self.framing_safety.max_zoom_in_change
                    ),
                    "purpose": "conservative_tunable_poc_guardrails",
                },
            },
        }


def _require_table(document: dict[str, object], name: str) -> dict[str, object]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a TOML table")
    return value


def _reject_unknown(actual: object, allowed: frozenset[str], context: str) -> None:
    if not isinstance(actual, dict):
        raise ValueError(f"{context} must be a TOML table")
    unknown = set(actual) - allowed
    if unknown:
        raise ValueError(f"unknown {context} field(s): {', '.join(sorted(unknown))}")


def _number(table: dict[str, object], field: str, *, positive: bool = False) -> float:
    value = table.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    converted = float(value)
    valid = math.isfinite(converted) and (converted > 0 if positive else converted >= 0)
    if not valid:
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{field} must be finite and {qualifier}")
    return converted


def loads_greedy_config(content: bytes | str) -> GreedySliceConfig:
    """Parse and strictly validate the v1 TOML configuration contract."""

    if isinstance(content, str):
        content = content.encode("utf-8")
    try:
        document = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"invalid greedy configuration TOML: {error}") from error

    _reject_unknown(document, _ROOT_KEYS, "root")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}")

    weights = _require_table(document, "weights")
    expected_weights = frozenset(INTEREST_SIGNAL_NAMES)
    _reject_unknown(weights, expected_weights, "weights")
    missing_weights = expected_weights - set(weights)
    if missing_weights:
        raise ValueError(
            f"missing editorial weight(s): {', '.join(sorted(missing_weights))}"
        )
    # Detector confidence is perception evidence only. The exact v1 allowlist
    # makes it impossible to introduce it (or another backend score) as an
    # editorial weight by configuration.
    scoring = ScoringConfig(
        tuple((name, _number(weights, name)) for name in INTEREST_SIGNAL_NAMES)
    )

    hysteresis = _require_table(document, "hysteresis")
    _reject_unknown(hysteresis, _HYSTERESIS_KEYS, "hysteresis")
    missing_hysteresis = _HYSTERESIS_KEYS - set(hysteresis)
    if missing_hysteresis:
        raise ValueError(
            f"missing hysteresis field(s): {', '.join(sorted(missing_hysteresis))}"
        )
    planner = GreedyConfig(
        minimum_dwell_seconds=_number(hysteresis, "minimum_dwell_seconds"),
        switch_margin=_number(hysteresis, "switch_margin"),
        challenger_hold_seconds=_number(hysteresis, "challenger_hold_seconds"),
    )

    camera = _require_table(document, "camera")
    _reject_unknown(camera, _CAMERA_KEYS, "camera")
    if "min_angular_change_degrees" not in camera:
        raise ValueError("missing camera field: min_angular_change_degrees")
    threshold_degrees = _number(
        camera, "min_angular_change_degrees", positive=True
    )
    if threshold_degrees > 180:
        raise ValueError("min_angular_change_degrees must be at most 180")
    required_framing = _CAMERA_KEYS - {"min_angular_change_degrees"}
    missing_framing = required_framing - set(camera)
    if missing_framing:
        raise ValueError(
            f"missing camera field(s): {', '.join(sorted(missing_framing))}"
        )
    minimum_fov = _number(
        camera, "minimum_horizontal_fov_degrees", positive=True
    )
    padding = _number(camera, "candidate_extent_padding_degrees")
    maximum_zoom_in = _number(
        camera, "maximum_zoom_in_change_degrees", positive=True
    )
    if minimum_fov >= 180:
        raise ValueError("minimum_horizontal_fov_degrees must be less than 180")
    if maximum_zoom_in >= 180:
        raise ValueError("maximum_zoom_in_change_degrees must be less than 180")

    return GreedySliceConfig(
        SCHEMA_VERSION,
        scoring,
        planner,
        math.radians(threshold_degrees),
        FramingSafetyConfig(
            minimum_h_fov=math.radians(minimum_fov),
            candidate_extent_padding=math.radians(padding),
            max_zoom_in_change=math.radians(maximum_zoom_in),
        ),
    )


def load_greedy_config(path: str | Path) -> GreedySliceConfig:
    """Load a version-controlled config without performing any network access."""

    return loads_greedy_config(Path(path).read_bytes())
