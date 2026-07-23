"""Dependency-light screen-space motion metrics for rendered flat video.

This deliberately estimates translation, not scene geometry.  It is useful as
an objective proxy for comparing two renders of the same source, but it cannot
separate camera motion from independently moving subjects or parallax.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MotionSample:
    time_seconds: float
    dx_pixels: int
    dy_pixels: int
    magnitude_pixels: float
    zero_sad: float
    best_sad: float


def estimate_translation(
    previous: bytes,
    current: bytes,
    width: int,
    height: int,
    *,
    search_radius: int = 8,
    pixel_stride: int = 2,
) -> tuple[int, int, float, float]:
    """Return (dx, dy, best_sad, zero_sad) using exhaustive block matching.

    ``dx`` and ``dy`` describe where content in ``previous`` moved in
    ``current``.  A positive dx means screen content moved right.
    """
    if len(previous) != width * height or len(current) != width * height:
        raise ValueError("frames must contain exactly width * height gray pixels")
    if width <= 2 * search_radius or height <= 2 * search_radius:
        raise ValueError("frame is too small for search_radius")
    if pixel_stride < 1:
        raise ValueError("pixel_stride must be positive")

    margin = search_radius

    def mean_absolute_difference(dx: int, dy: int) -> float:
        total = 0
        count = 0
        for y in range(margin, height - margin, pixel_stride):
            previous_row = y * width
            current_row = (y + dy) * width
            for x in range(margin, width - margin, pixel_stride):
                total += abs(
                    previous[previous_row + x] - current[current_row + x + dx]
                )
                count += 1
        return total / count

    zero_sad = mean_absolute_difference(0, 0)
    best = (zero_sad, 0, 0)
    for dy in range(-search_radius, search_radius + 1):
        for dx in range(-search_radius, search_radius + 1):
            score = mean_absolute_difference(dx, dy)
            # Stable tie-breaking prefers the smallest motion.
            candidate = (score, dx * dx + dy * dy, abs(dy), abs(dx), dx, dy)
            incumbent = (
                best[0],
                best[1] * best[1] + best[2] * best[2],
                abs(best[2]),
                abs(best[1]),
                best[1],
                best[2],
            )
            if candidate < incumbent:
                best = (score, dx, dy)
    return best[1], best[2], best[0], zero_sad


def motion_samples(
    frames: Iterable[bytes],
    width: int,
    height: int,
    fps: float,
    *,
    search_radius: int = 8,
    pixel_stride: int = 2,
) -> list[MotionSample]:
    iterator = iter(frames)
    try:
        previous = next(iterator)
    except StopIteration:
        return []
    samples: list[MotionSample] = []
    for frame_index, current in enumerate(iterator, start=1):
        dx, dy, best_sad, zero_sad = estimate_translation(
            previous,
            current,
            width,
            height,
            search_radius=search_radius,
            pixel_stride=pixel_stride,
        )
        samples.append(
            MotionSample(
                time_seconds=frame_index / fps,
                dx_pixels=dx,
                dy_pixels=dy,
                magnitude_pixels=math.hypot(dx, dy),
                zero_sad=zero_sad,
                best_sad=best_sad,
            )
        )
        previous = current
    return samples


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def summarize_samples(
    samples: Sequence[MotionSample], width: int, *, segment_fraction: float = 0.2
) -> dict[str, object]:
    """Summarize all samples plus equal-sized leading and trailing windows."""
    if not 0 < segment_fraction <= 0.5:
        raise ValueError("segment_fraction must be in (0, 0.5]")

    def summarize(window: Sequence[MotionSample]) -> dict[str, float | int]:
        magnitudes = [sample.magnitude_pixels for sample in window]
        vector_changes = [
            math.hypot(right.dx_pixels - left.dx_pixels, right.dy_pixels - left.dy_pixels)
            for left, right in zip(window, window[1:])
        ]
        improvements = [
            max(0.0, sample.zero_sad - sample.best_sad) for sample in window
        ]
        return {
            "pair_count": len(window),
            "median_step_pixels": _percentile(magnitudes, 0.5),
            "p95_step_pixels": _percentile(magnitudes, 0.95),
            "median_step_width_fraction": _percentile(magnitudes, 0.5) / width,
            "p95_step_width_fraction": _percentile(magnitudes, 0.95) / width,
            "median_vector_change_pixels": _percentile(vector_changes, 0.5),
            "p95_vector_change_pixels": _percentile(vector_changes, 0.95),
            "median_match_improvement_gray_levels": (
                statistics.median(improvements) if improvements else 0.0
            ),
        }

    edge_count = max(1, math.ceil(len(samples) * segment_fraction)) if samples else 0
    first = samples[:edge_count]
    last = samples[-edge_count:] if edge_count else []
    first_summary = summarize(first)
    last_summary = summarize(last)
    first_median = float(first_summary["median_vector_change_pixels"])
    last_median = float(last_summary["median_vector_change_pixels"])
    return {
        "all": summarize(samples),
        "first": first_summary,
        "last": last_summary,
        "last_vs_first_median_vector_change_ratio": (
            last_median / first_median
            if first_median > 0
            else (0.0 if last_median == 0 else None)
        ),
    }
