"""Classify invalid local-rotation runs without synthesizing motion."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class GapRun:
    start_step_index: int
    end_step_index: int
    frame_count: int
    start_pts_seconds: float
    end_pts_seconds: float
    classification: str
    reason: str


def classify_gap_runs(
    steps: list[dict], *, maximum_interior_gap_frames: int
) -> list[GapRun]:
    if maximum_interior_gap_frames < 0:
        raise ValueError("maximum interior gap frames must be nonnegative")
    if not steps:
        raise ValueError("steps must not be empty")

    runs = []
    start = None
    for index in range(len(steps) + 1):
        invalid = (
            index < len(steps) and steps[index].get("state") != "measured"
        )
        if invalid and start is None:
            start = index
        if not invalid and start is not None:
            end = index - 1
            frame_count = end - start + 1
            boundary = start == 0 or end == len(steps) - 1
            if boundary:
                classification = "unbridgeable"
                reason = "boundary_gap_has_no_two_sided_rotation_context"
            elif frame_count <= maximum_interior_gap_frames:
                classification = "bridge_candidate"
                reason = "bounded_interior_gap_requires_validation"
            else:
                classification = "unbridgeable"
                reason = "interior_gap_exceeds_configured_frame_bound"
            runs.append(GapRun(
                start_step_index=start,
                end_step_index=end,
                frame_count=frame_count,
                start_pts_seconds=float(
                    steps[start]["previous_pts_seconds"]
                ),
                end_pts_seconds=float(steps[end]["current_pts_seconds"]),
                classification=classification,
                reason=reason,
            ))
            start = None
    return runs


def bridge_candidate_gaps(
    steps: list[dict], *, maximum_interior_gap_frames: int
) -> list[dict]:
    """SLERP local rotations across classified short interior gaps."""

    output = [dict(step) for step in steps]
    for run in classify_gap_runs(
        steps,
        maximum_interior_gap_frames=maximum_interior_gap_frames,
    ):
        if run.classification != "bridge_candidate":
            continue
        before = steps[run.start_step_index - 1]["rotation_xyzw"]
        after = steps[run.end_step_index + 1]["rotation_xyzw"]
        if before is None or after is None:
            raise ValueError("bridge candidate lacks two measured rotations")
        denominator = run.frame_count + 1
        for offset, index in enumerate(
            range(run.start_step_index, run.end_step_index + 1), start=1
        ):
            output[index]["rotation_xyzw"] = list(
                _slerp(before, after, offset / denominator)
            )
            output[index]["state"] = "interpolated"
            output[index]["interpolation"] = {
                "method": "local-step-slerp",
                "gap_frame_count": run.frame_count,
                "fraction": offset / denominator,
            }
    return output


def _slerp(first, second, fraction):
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("SLERP fraction must be in [0, 1]")
    left = _unit_quaternion(first)
    right = _unit_quaternion(second)
    dot = sum(a * b for a, b in zip(left, right))
    if dot < 0.0:
        right = tuple(-value for value in right)
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        blended = tuple(
            (1.0 - fraction) * a + fraction * b
            for a, b in zip(left, right)
        )
        return _unit_quaternion(blended)
    angle = math.acos(dot)
    scale = math.sin(angle)
    left_weight = math.sin((1.0 - fraction) * angle) / scale
    right_weight = math.sin(fraction * angle) / scale
    return tuple(
        left_weight * a + right_weight * b
        for a, b in zip(left, right)
    )


def _unit_quaternion(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("quaternion must contain four values")
    if any(
        not isinstance(item, (int, float))
        or isinstance(item, bool)
        or not math.isfinite(item)
        for item in value
    ):
        raise ValueError("quaternion must contain finite values")
    norm = math.sqrt(sum(item * item for item in value))
    if norm < 1e-12:
        raise ValueError("quaternion must be nonzero")
    return tuple(item / norm for item in value)
