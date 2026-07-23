import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.camera_path import (  # noqa: E402
    CameraKeyframe,
    CameraSample,
    format_ffmpeg_sendcmd,
    interpolate_path,
    keyframe_continuity,
    segment_limits,
)


class CameraPathInterpolationTests(unittest.TestCase):
    def test_seam_crossing_takes_shortest_yaw_path_without_overshoot(self):
        path = interpolate_path(
            (
                CameraKeyframe(0.0, math.radians(179), 0.0, math.radians(90)),
                CameraKeyframe(1.0, math.radians(-179), 0.0, math.radians(90)),
            ),
            fps=10,
        )
        degrees = [math.degrees(sample.yaw) for sample in path]
        self.assertAlmostEqual(degrees[0], 179.0)
        self.assertAlmostEqual(degrees[-1], 181.0)
        self.assertTrue(all(left <= right for left, right in zip(degrees, degrees[1:])))
        self.assertTrue(all(179.0 <= yaw <= 181.0 for yaw in degrees))

    def test_keyframes_on_frame_grid_are_reproduced_exactly(self):
        keyframes = (
            CameraKeyframe(0.0, 0.0, 0.0, math.radians(90)),
            CameraKeyframe(0.5, 1.0, 0.25, math.radians(70)),
            CameraKeyframe(1.0, 0.5, -0.25, math.radians(100)),
        )
        path = interpolate_path(keyframes, fps=10)
        for frame, keyframe in ((0, keyframes[0]), (5, keyframes[1]), (10, keyframes[2])):
            self.assertEqual(path[frame].time, keyframe.time)
            self.assertAlmostEqual(path[frame].yaw, keyframe.yaw)
            self.assertAlmostEqual(path[frame].pitch, keyframe.pitch)
            self.assertAlmostEqual(path[frame].h_fov, keyframe.h_fov)

    def test_pitch_and_fov_do_not_overshoot_near_pole(self):
        path = interpolate_path(
            (
                CameraKeyframe(0.0, 0.0, math.radians(80), math.radians(100)),
                CameraKeyframe(2.0, math.pi, math.radians(89.9), math.radians(40)),
            ),
            fps=30,
        )
        self.assertTrue(all(math.isfinite(value) for sample in path for value in (sample.yaw, sample.pitch, sample.h_fov)))
        self.assertTrue(all(math.radians(80) <= sample.pitch <= math.radians(89.9) for sample in path))
        self.assertTrue(all(math.radians(40) <= sample.h_fov <= math.radians(100) for sample in path))

    def test_quintic_segment_has_declared_finite_derivative_bounds(self):
        start = CameraKeyframe(0.0, 0.0, 0.0, math.radians(90))
        end = CameraKeyframe(2.0, math.radians(60), math.radians(20), math.radians(70))
        limits = segment_limits(start, end)
        self.assertAlmostEqual(limits.max_yaw_velocity, math.radians(56.25))
        self.assertAlmostEqual(
            limits.max_yaw_acceleration,
            math.radians(60) * 10 * math.sqrt(3) / 12,
        )
        self.assertGreater(limits.max_pitch_velocity, 0.0)
        self.assertGreater(limits.max_fov_acceleration, 0.0)
        self.assertAlmostEqual(limits.max_yaw_jerk, math.radians(450))

    def test_multi_segment_path_is_c2_but_exposes_jerk_jump(self):
        reports = keyframe_continuity(
            (
                CameraKeyframe(0.0, math.radians(0), 0.0, math.radians(90)),
                CameraKeyframe(2.0, math.radians(40), math.radians(10), math.radians(80)),
                CameraKeyframe(3.0, math.radians(10), math.radians(10), math.radians(100)),
            )
        )
        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report.time, 2.0)
        self.assertEqual(report.left_velocity, (0.0, 0.0, 0.0))
        self.assertEqual(report.right_velocity, (0.0, 0.0, 0.0))
        self.assertEqual(report.left_acceleration, (0.0, 0.0, 0.0))
        self.assertEqual(report.right_acceleration, (0.0, 0.0, 0.0))
        self.assertAlmostEqual(report.left_jerk[0], math.radians(300))
        self.assertAlmostEqual(report.right_jerk[0], math.radians(-1800))
        self.assertAlmostEqual(report.jerk_jump[0], math.radians(-2100))
        self.assertAlmostEqual(report.jerk_jump[1], math.radians(-75))
        self.assertAlmostEqual(report.jerk_jump[2], math.radians(1275))

    def test_continuity_metrics_unwrap_yaw_before_measuring(self):
        report = keyframe_continuity(
            (
                CameraKeyframe(0.0, math.radians(178), 0.0, math.radians(90)),
                CameraKeyframe(1.0, math.radians(-179), 0.0, math.radians(90)),
                CameraKeyframe(2.0, math.radians(-176), 0.0, math.radians(90)),
            )
        )[0]
        self.assertAlmostEqual(report.left_jerk[0], math.radians(180))
        self.assertAlmostEqual(report.right_jerk[0], math.radians(180))
        self.assertAlmostEqual(report.jerk_jump[0], 0.0, places=12)

    def test_invalid_timing_pitch_fov_and_fps_are_rejected(self):
        valid = CameraKeyframe(0.0, 0.0, 0.0, math.radians(90))
        with self.assertRaises(ValueError):
            interpolate_path((), 30)
        with self.assertRaises(ValueError):
            interpolate_path((valid,), 0)
        with self.assertRaises(ValueError):
            interpolate_path((valid, valid), 30)
        with self.assertRaises(ValueError):
            interpolate_path((CameraKeyframe(0, 0, math.pi, 1),), 30)
        with self.assertRaises(ValueError):
            interpolate_path((CameraKeyframe(0, 0, 0, math.pi),), 30)


class SendcmdFormattingTests(unittest.TestCase):
    def test_dense_samples_format_degrees_for_default_v360_target(self):
        commands = format_ffmpeg_sendcmd(
            (
                CameraSample(0, 0.0, math.pi, math.pi / 4, math.pi / 2),
                CameraSample(1, 0.1, math.pi + 0.1, 0.0, math.pi / 3),
            )
        )
        lines = commands.splitlines()
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[0], "0.000000000 v360 yaw -180.000000000;")
        self.assertEqual(lines[1], "0.000000000 v360 pitch 45.000000000;")
        self.assertEqual(lines[2], "0.000000000 v360 h_fov 90.000000000;")
        self.assertTrue(lines[3].startswith("0.100000000 v360 yaw -174.270"))

    def test_unwrapped_seam_path_is_wrapped_only_at_renderer_boundary(self):
        path = interpolate_path(
            (
                CameraKeyframe(0.0, math.radians(179), 0.0, math.radians(90)),
                CameraKeyframe(1.0, math.radians(-179), 0.0, math.radians(90)),
            ),
            fps=2,
        )
        yaw_commands = format_ffmpeg_sendcmd(path).splitlines()[::3]
        self.assertIn("yaw 179.000000000", yaw_commands[0])
        self.assertIn("yaw -180.000000000", yaw_commands[1])
        self.assertIn("yaw -179.000000000", yaw_commands[2])


if __name__ == "__main__":
    unittest.main()
