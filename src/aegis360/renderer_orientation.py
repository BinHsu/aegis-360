"""Quaternion composition and FFmpeg-v360 yaw/pitch/roll conversion."""

import math


def stabilization_correction(raw_xyzw, smoothed_xyzw):
    """Return ``inverse(raw) * smoothed`` in the project composition order."""

    raw = _unit(raw_xyzw)
    smooth = _unit(smoothed_xyzw)
    return _multiply((-raw[0], -raw[1], -raw[2], raw[3]), smooth)


def quaternion_to_v360_yaw_pitch_roll(rotation_xyzw):
    """Extract ``R_y(yaw) R_x(-pitch) R_z(roll)`` angles in radians."""

    x, y, z, w = _unit(rotation_xyzw)
    matrix = (
        1 - 2 * (y * y + z * z),
        2 * (x * y - z * w),
        2 * (x * z + y * w),
        2 * (x * y + z * w),
        1 - 2 * (x * x + z * z),
        2 * (y * z - x * w),
        2 * (x * z - y * w),
        2 * (y * z + x * w),
        1 - 2 * (x * x + y * y),
    )
    pitch = math.asin(max(-1.0, min(1.0, matrix[5])))
    cosine_pitch = math.cos(pitch)
    if abs(cosine_pitch) < 1e-7:
        raise ValueError("v360 yaw/pitch/roll is singular at the pitch pole")
    yaw = math.atan2(matrix[2], matrix[8])
    roll = math.atan2(matrix[3], matrix[4])
    return yaw, pitch, roll


def v360_yaw_pitch_roll_to_quaternion(yaw, pitch, roll):
    return _multiply(
        _axis_angle((0.0, 1.0, 0.0), yaw),
        _multiply(
            _axis_angle((1.0, 0.0, 0.0), -pitch),
            _axis_angle((0.0, 0.0, 1.0), roll),
        ),
    )


def _axis_angle(axis, angle):
    scale = math.sin(angle / 2.0)
    return (
        axis[0] * scale, axis[1] * scale, axis[2] * scale,
        math.cos(angle / 2.0),
    )


def _multiply(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return _unit((
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ))


def _unit(value):
    if len(value) != 4 or any(not math.isfinite(item) for item in value):
        raise ValueError("quaternion must contain four finite values")
    norm = math.sqrt(sum(item * item for item in value))
    if norm < 1e-12:
        raise ValueError("quaternion must be nonzero")
    return tuple(item / norm for item in value)
