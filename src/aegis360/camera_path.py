"""Dependency-free interpolation for dense virtual-camera control paths.

The planner-facing yaw values are unwrapped before interpolation, so a segment
crossing the ERP seam follows the shortest yaw displacement.  Each segment
uses quintic smootherstep, ``6s^5 - 15s^4 + 10s^3``.  It is monotone, has no
coordinate overshoot, and has zero velocity and acceleration at both ends.

This is deliberately coordinate interpolation rather than spherical linear
interpolation.  Pitch is constrained to the physical latitude range, which
keeps the path finite and prevents pole overshoot; callers should avoid using
yaw to express intent exactly at a pole, where yaw is geometrically undefined.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from .geometry import HALF_PI, spherical_distance, unwrap_yaw, wrap_yaw


@dataclass(frozen=True)
class CameraKeyframe:
    """A timestamped camera pose, with angles and horizontal FOV in radians."""

    time: float
    yaw: float
    pitch: float
    h_fov: float


@dataclass(frozen=True)
class CameraSample:
    """A dense camera pose suitable for one output frame."""

    frame: int
    time: float
    yaw: float
    pitch: float
    h_fov: float


def greedy_trace_to_keyframes(
    trace: Mapping[str, object],
    duration: float,
    direction_threshold: float = math.radians(5.0),
) -> tuple[CameraKeyframe, ...]:
    """Adapt greedy decisions to sparse, clip-relative camera keyframes.

    The trace may use arbitrary nonnegative analysis timestamps.  They are
    rebased so the first decision is at zero, and ``duration`` is the resulting
    clip duration.  Interior keyframes are emitted only when the selected
    candidate ID changes or its spherical direction has moved at least
    ``direction_threshold`` from the last emitted keyframe.  Required start and
    end keyframes are added even when neither condition fires.
    """

    if not math.isfinite(duration) or duration < 0.0:
        raise ValueError("duration must be finite and nonnegative")
    if not math.isfinite(direction_threshold) or direction_threshold < 0.0:
        raise ValueError("direction threshold must be finite and nonnegative")

    decisions_object = trace.get("decisions")
    if not isinstance(decisions_object, (list, tuple)) or not decisions_object:
        raise ValueError("greedy trace requires at least one decision")

    decisions: list[tuple[float, str, CameraKeyframe]] = []
    previous_timestamp = -math.inf
    for decision_object in decisions_object:
        if not isinstance(decision_object, Mapping):
            raise ValueError("greedy decisions must be mappings")
        timestamp = decision_object.get("timestamp")
        selected_id = decision_object.get("selected_candidate_id")
        candidates = decision_object.get("candidates")
        if (
            not isinstance(timestamp, (int, float))
            or isinstance(timestamp, bool)
            or not math.isfinite(timestamp)
            or timestamp < 0.0
            or timestamp <= previous_timestamp
        ):
            raise ValueError("greedy decision timestamps must be finite and increasing")
        if not isinstance(selected_id, str) or not selected_id:
            raise ValueError("greedy decisions require a selected candidate ID")
        if not isinstance(candidates, (list, tuple)):
            raise ValueError("greedy decisions require candidate geometry")

        selected = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, Mapping)
                and candidate.get("candidate_id") == selected_id
            ),
            None,
        )
        if selected is None:
            raise ValueError("selected candidate geometry is missing from decision")
        geometry = (
            selected.get("yaw_radians"),
            selected.get("pitch_radians"),
            selected.get("h_fov_radians"),
        )
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in geometry
        ):
            raise ValueError("selected candidate geometry must be finite")
        yaw, pitch, h_fov = geometry
        # Reuse the camera-path validation rules below after timestamps are
        # rebased; retaining the source timestamp here keeps this adapter small.
        decisions.append(
            (float(timestamp), selected_id, CameraKeyframe(0.0, yaw, pitch, h_fov))
        )
        previous_timestamp = float(timestamp)

    origin = decisions[0][0]
    relative_end = decisions[-1][0] - origin
    if relative_end > duration + 1e-12:
        raise ValueError("greedy decisions extend beyond the clip duration")

    first = decisions[0]
    keyframes = [CameraKeyframe(0.0, first[2].yaw, first[2].pitch, first[2].h_fov)]
    emitted_id = first[1]
    emitted_pose = first[2]
    for timestamp, selected_id, pose in decisions[1:]:
        relative_time = timestamp - origin
        direction_change = spherical_distance(
            (emitted_pose.yaw, emitted_pose.pitch), (pose.yaw, pose.pitch)
        )
        if selected_id != emitted_id or direction_change >= direction_threshold:
            keyframes.append(
                CameraKeyframe(relative_time, pose.yaw, pose.pitch, pose.h_fov)
            )
            emitted_id = selected_id
            emitted_pose = pose

    final_pose = decisions[-1][2]
    if duration > 0.0 and keyframes[-1].time < duration:
        keyframes.append(
            CameraKeyframe(duration, final_pose.yaw, final_pose.pitch, final_pose.h_fov)
        )
    return _validate_keyframes(keyframes)


def greedy_trace_to_camera_path(
    trace: Mapping[str, object],
    duration: float,
    direction_threshold: float = math.radians(5.0),
) -> dict[str, object]:
    """Return the sparse adapter result in the orchestrator JSON contract."""

    keyframes = greedy_trace_to_keyframes(trace, duration, direction_threshold)
    decisions = trace["decisions"]
    assert isinstance(decisions, (list, tuple))  # validated by the call above
    first = decisions[0]
    assert isinstance(first, Mapping)
    origin = float(first["timestamp"])

    ids_by_time = {
        float(decision["timestamp"]) - origin: decision["selected_candidate_id"]
        for decision in decisions
        if isinstance(decision, Mapping)
    }
    final = decisions[-1]
    assert isinstance(final, Mapping)
    rows = []
    for index, keyframe in enumerate(keyframes):
        if index == 0:
            selected_id = first["selected_candidate_id"]
        elif index == len(keyframes) - 1:
            selected_id = final["selected_candidate_id"]
        else:
            selected_id = ids_by_time[keyframe.time]
        rows.append(
            {
                "timestamp": keyframe.time,
                "yaw": keyframe.yaw,
                "pitch": keyframe.pitch,
                "h_fov": keyframe.h_fov,
                "selected_candidate_id": selected_id,
            }
        )
    return {
        "schema_version": "aegis360.camera-path.v1",
        "coordinate_units": "radians",
        "keyframes": rows,
    }


def camera_path_document_to_keyframes(
    document: Mapping[str, object],
) -> tuple[CameraKeyframe, ...]:
    """Load the orchestrator JSON contract for interpolation/sendcmd."""

    if document.get("schema_version") != "aegis360.camera-path.v1":
        raise ValueError("unsupported camera path schema version")
    if document.get("coordinate_units") != "radians":
        raise ValueError("camera path coordinate units must be radians")
    rows = document.get("keyframes")
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("camera path requires at least one keyframe")
    try:
        keyframes = tuple(
            CameraKeyframe(
                row["timestamp"], row["yaw"], row["pitch"], row["h_fov"]
            )
            for row in rows
            if isinstance(row, Mapping)
        )
    except (KeyError, TypeError) as error:
        raise ValueError("camera path keyframe geometry is incomplete") from error
    if len(keyframes) != len(rows):
        raise ValueError("camera path keyframes must be mappings")
    return _validate_keyframes(keyframes)


@dataclass(frozen=True)
class SegmentLimits:
    """Analytic per-coordinate derivative bounds for one smooth segment."""

    max_yaw_velocity: float
    max_pitch_velocity: float
    max_fov_velocity: float
    max_yaw_acceleration: float
    max_pitch_acceleration: float
    max_fov_acceleration: float
    max_yaw_jerk: float
    max_pitch_jerk: float
    max_fov_jerk: float


@dataclass(frozen=True)
class KeyframeContinuity:
    """One-sided coordinate derivatives at an interior path keyframe.

    The three-value tuples are yaw, pitch and horizontal FOV, in that order.
    Angular units are radians.  Smootherstep makes velocity and acceleration
    zero on both sides, while jerk generally changes at the join.
    """

    time: float
    left_velocity: tuple[float, float, float]
    right_velocity: tuple[float, float, float]
    left_acceleration: tuple[float, float, float]
    right_acceleration: tuple[float, float, float]
    left_jerk: tuple[float, float, float]
    right_jerk: tuple[float, float, float]

    @property
    def jerk_jump(self) -> tuple[float, float, float]:
        """Return right-minus-left jerk at the keyframe."""

        return tuple(
            right - left for left, right in zip(self.left_jerk, self.right_jerk)
        )


def _validate_keyframes(keyframes: Iterable[CameraKeyframe]) -> tuple[CameraKeyframe, ...]:
    frames = tuple(keyframes)
    if not frames:
        raise ValueError("at least one camera keyframe is required")

    previous_time = -math.inf
    unwrapped: list[CameraKeyframe] = []
    for keyframe in frames:
        values = (keyframe.time, keyframe.yaw, keyframe.pitch, keyframe.h_fov)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("camera keyframes must contain only finite values")
        if keyframe.time < 0.0 or keyframe.time <= previous_time:
            raise ValueError("camera keyframe times must be nonnegative and increasing")
        if not -HALF_PI <= keyframe.pitch <= HALF_PI:
            raise ValueError("camera pitch must remain between the poles")
        if not 0.0 < keyframe.h_fov < math.pi:
            raise ValueError("horizontal FOV must be between zero and pi radians")

        yaw = keyframe.yaw
        if unwrapped:
            yaw = unwrap_yaw(yaw, unwrapped[-1].yaw)
        unwrapped.append(
            CameraKeyframe(keyframe.time, yaw, keyframe.pitch, keyframe.h_fov)
        )
        previous_time = keyframe.time
    return tuple(unwrapped)


def _smootherstep(position: float) -> float:
    position = min(1.0, max(0.0, position))
    return position**3 * (position * (position * 6.0 - 15.0) + 10.0)


def _bounded_lerp(start: float, end: float, weight: float) -> float:
    """Interpolate without allowing floating-point rounding past an endpoint."""

    value = start + weight * (end - start)
    return min(max(start, end), max(min(start, end), value))


def interpolate_path(
    keyframes: Iterable[CameraKeyframe], fps: float
) -> tuple[CameraSample, ...]:
    """Sample an inclusive, per-frame path from sparse camera keyframes.

    Samples begin at frame zero and end at the last frame timestamp not later
    than the final keyframe.  If the final keyframe lies exactly on the frame
    grid it is included.  Keyframes before time zero are intentionally invalid.
    """

    if not math.isfinite(fps) or fps <= 0.0:
        raise ValueError("fps must be finite and positive")
    path = _validate_keyframes(keyframes)
    last_frame = math.floor(path[-1].time * fps + 1e-12)
    samples: list[CameraSample] = []
    segment = 0

    for frame in range(last_frame + 1):
        timestamp = frame / fps
        while segment + 1 < len(path) and timestamp > path[segment + 1].time:
            segment += 1

        if timestamp <= path[0].time or len(path) == 1:
            pose = path[0]
            yaw, pitch, h_fov = pose.yaw, pose.pitch, pose.h_fov
        elif segment + 1 >= len(path):
            pose = path[-1]
            yaw, pitch, h_fov = pose.yaw, pose.pitch, pose.h_fov
        else:
            start, end = path[segment], path[segment + 1]
            progress = (timestamp - start.time) / (end.time - start.time)
            weight = _smootherstep(progress)
            yaw = _bounded_lerp(start.yaw, end.yaw, weight)
            pitch = _bounded_lerp(start.pitch, end.pitch, weight)
            h_fov = _bounded_lerp(start.h_fov, end.h_fov, weight)

        samples.append(CameraSample(frame, timestamp, yaw, pitch, h_fov))
    return tuple(samples)


def segment_limits(first: CameraKeyframe, second: CameraKeyframe) -> SegmentLimits:
    """Return exact maxima implied by quintic interpolation for a segment.

    Smootherstep's maximum normalized speed is 15/8 and its maximum absolute
    normalized acceleration is 10*sqrt(3)/3.  Bounds are per yaw, pitch and
    FOV coordinate in radians/s, radians/s^2 and radians/s^3, respectively.
    """

    first, second = _validate_keyframes((first, second))
    duration = second.time - first.time
    speed_scale = 15.0 / (8.0 * duration)
    acceleration_scale = 10.0 * math.sqrt(3.0) / (3.0 * duration * duration)
    jerk_scale = 60.0 / (duration * duration * duration)
    deltas = (
        abs(second.yaw - first.yaw),
        abs(second.pitch - first.pitch),
        abs(second.h_fov - first.h_fov),
    )
    return SegmentLimits(
        *(delta * speed_scale for delta in deltas),
        *(delta * acceleration_scale for delta in deltas),
        *(delta * jerk_scale for delta in deltas),
    )


def keyframe_continuity(
    keyframes: Iterable[CameraKeyframe],
) -> tuple[KeyframeContinuity, ...]:
    """Measure exact one-sided derivatives at every interior keyframe.

    Metrics are for the interpolated yaw, pitch and FOV coordinates.  They are
    reproducible and useful as a planner gate, but they are not a perceptual
    comfort model and no comfort threshold is implied.
    """

    path = _validate_keyframes(keyframes)
    reports: list[KeyframeContinuity] = []
    zero = (0.0, 0.0, 0.0)
    for index in range(1, len(path) - 1):
        previous, current, following = path[index - 1 : index + 2]
        left_duration = current.time - previous.time
        right_duration = following.time - current.time
        left_deltas = (
            current.yaw - previous.yaw,
            current.pitch - previous.pitch,
            current.h_fov - previous.h_fov,
        )
        right_deltas = (
            following.yaw - current.yaw,
            following.pitch - current.pitch,
            following.h_fov - current.h_fov,
        )
        reports.append(
            KeyframeContinuity(
                time=current.time,
                left_velocity=zero,
                right_velocity=zero,
                left_acceleration=zero,
                right_acceleration=zero,
                left_jerk=tuple(
                    60.0 * delta / left_duration**3 for delta in left_deltas
                ),
                right_jerk=tuple(
                    60.0 * delta / right_duration**3 for delta in right_deltas
                ),
            )
        )
    return tuple(reports)


def format_ffmpeg_sendcmd(samples: Iterable[CameraSample]) -> str:
    """Format dense samples as commands for the default FFmpeg ``v360`` target."""

    lines: list[str] = []
    previous_time = -math.inf
    for sample in samples:
        values = (sample.time, sample.yaw, sample.pitch, sample.h_fov)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("camera samples must contain only finite values")
        if sample.frame < 0 or sample.time < 0.0 or sample.time < previous_time:
            raise ValueError("camera samples must be chronological and nonnegative")
        timestamp = f"{sample.time:.9f}"
        lines.extend(
            (
                f"{timestamp} v360 yaw {math.degrees(wrap_yaw(sample.yaw)):.9f};",
                f"{timestamp} v360 pitch {math.degrees(sample.pitch):.9f};",
                f"{timestamp} v360 h_fov {math.degrees(sample.h_fov):.9f};",
            )
        )
        previous_time = sample.time
    return "\n".join(lines) + ("\n" if lines else "")
