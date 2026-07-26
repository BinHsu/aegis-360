"""Accumulate connected local rotations into independently anchored segments."""

import math


def build_relative_rotation_segments(steps: list[dict]) -> list[dict]:
    if not steps:
        raise ValueError("steps must not be empty")
    segments = []
    current = None
    orientation = (0.0, 0.0, 0.0, 1.0)
    for index, step in enumerate(steps):
        rotation = step.get("rotation_xyzw")
        usable = step.get("state") in {"measured", "interpolated"}
        if not usable or rotation is None:
            if current is not None:
                segments.append(current)
                current = None
            orientation = (0.0, 0.0, 0.0, 1.0)
            continue
        if current is None:
            start = float(step["previous_pts_seconds"])
            current = {
                "start_step_index": index,
                "end_step_index": index,
                "anchor_pts_seconds": start,
                "anchor_semantics": "identity_relative_to_segment_start",
                "samples": [{
                    "pts_seconds": start,
                    "relative_orientation_xyzw": list(orientation),
                    "source_step_state": "segment_anchor",
                }],
            }
        orientation = _multiply_continuous(
            orientation, _unit_quaternion(rotation)
        )
        current["end_step_index"] = index
        current["samples"].append({
            "pts_seconds": float(step["current_pts_seconds"]),
            "relative_orientation_xyzw": list(orientation),
            "source_step_state": step["state"],
        })
    if current is not None:
        segments.append(current)
    return segments


def _multiply_continuous(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    result = (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )
    result = _unit_quaternion(result)
    dot = sum(a * b for a, b in zip(first, result))
    return tuple(-value for value in result) if dot < 0.0 else result


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
