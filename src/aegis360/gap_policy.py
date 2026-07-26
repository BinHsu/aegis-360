"""Classify invalid local-rotation runs without synthesizing motion."""

from dataclasses import dataclass


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
