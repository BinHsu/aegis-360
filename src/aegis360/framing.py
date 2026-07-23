"""Conservative, tunable framing guards for POC camera poses.

These limits reduce accidental tight crops.  They are engineering safeguards,
not claims about perceptual comfort or an optimal field of view.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class FramingSafetyConfig:
    """Horizontal framing limits, expressed in radians.

    ``candidate_extent_padding`` is applied on *each* horizontal side, so a
    candidate extent of 80 degrees with 10 degrees of padding requests a
    100-degree viewport. ``max_zoom_in_change`` limits how much narrower the
    next decision or shot may become; zooming out remains unrestricted.
    """

    minimum_h_fov: float = math.radians(110.0)
    candidate_extent_padding: float = math.radians(10.0)
    max_zoom_in_change: float = math.radians(15.0)

    def __post_init__(self) -> None:
        values = (
            self.minimum_h_fov,
            self.candidate_extent_padding,
            self.max_zoom_in_change,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("framing safety values must be finite")
        if not 0 < self.minimum_h_fov < math.pi:
            raise ValueError("minimum horizontal FOV must be in (0, pi)")
        if self.candidate_extent_padding < 0:
            raise ValueError("candidate extent padding must be nonnegative")
        if self.max_zoom_in_change <= 0 or self.max_zoom_in_change >= math.pi:
            raise ValueError("maximum zoom-in change must be in (0, pi)")


def safe_horizontal_fovs(
    candidate_extents: Iterable[float],
    config: FramingSafetyConfig,
) -> tuple[float, ...]:
    """Return guarded FOVs in order, enforcing the zoom-in delta per item."""

    output: list[float] = []
    largest_representable_fov = math.nextafter(math.pi, 0.0)
    for extent in candidate_extents:
        if not math.isfinite(extent) or not 0 < extent < math.pi:
            raise ValueError("candidate horizontal extent must be in (0, pi)")
        padded = extent + 2.0 * config.candidate_extent_padding
        guarded = min(
            largest_representable_fov,
            max(config.minimum_h_fov, padded),
        )
        if output:
            guarded = max(guarded, output[-1] - config.max_zoom_in_change)
        output.append(guarded)
    return tuple(output)
