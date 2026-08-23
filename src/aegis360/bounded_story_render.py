"""Renderer filter/trace construction for a validated bounded story plan."""

from __future__ import annotations

from typing import Mapping


def build_bounded_story_filter_graph(
    plan: Mapping[str, object], grid: Mapping[str, object], *,
    width: int, height: int,
) -> tuple[str, str, str]:
    if (isinstance(width, bool) or isinstance(height, bool)
            or not 320 <= width <= 1920 or not 180 <= height <= 1080):
        raise ValueError("bounded story render dimensions are invalid")
    geometry = {item["candidate_id"]: item for item in grid["candidates"]}
    decisions = plan.get("decisions", [])
    if not decisions:
        raise ValueError("bounded story render plan is empty")
    filters = []
    labels = []
    for index, decision in enumerate(decisions):
        candidate = geometry.get(decision["selected_candidate_id"])
        if candidate is None:
            raise ValueError("bounded story render candidate is undeclared")
        if index and decisions[index - 1]["end_seconds"] != decision["start_seconds"]:
            raise ValueError("bounded story render decisions must be contiguous")
        label = f"v{index}"
        labels.append(f"[{label}]")
        filters.append(
            f"[0:v:0]trim=start={decision['start_seconds']}:end={decision['end_seconds']},"
            "setpts=PTS-STARTPTS,"
            f"v360=input=equirect:output=flat:w={width}:h={height}:"
            f"yaw={candidate['yaw_degrees']}:pitch={candidate['pitch_degrees']}:"
            f"h_fov={candidate['horizontal_fov_degrees']}:interp=linear[{label}]"
        )
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[vout]")
    start = plan["window"]["start_seconds"]
    end = plan["window"]["end_seconds"]
    filters.append(
        f"[0:a:0]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[aout]"
    )
    return ";".join(filters), "[vout]", "[aout]"
