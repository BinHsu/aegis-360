import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.so3 import fit_rotation, rotate_ray
from aegis360.viewport_rays import (
    RectilinearViewport,
    homography_to_world_rays,
    pixel_matches_to_world_rays,
    pixel_to_world_ray,
    viewport_normalized_to_world_ray,
)


def axis_angle(axis, angle):
    scale = math.sin(angle / 2.0)
    return (axis[0] * scale, axis[1] * scale, axis[2] * scale, math.cos(angle / 2.0))


def world_ray_to_pixel(ray, viewport):
    # Tests use an unrotated viewport so the inverse projection is direct.
    self_dot = sum(value * value for value in ray)
    assert abs(self_dot - 1.0) < 1e-9 and ray[2] > 0.0
    focal = viewport.width / (2.0 * math.tan(viewport.horizontal_fov / 2.0))
    return (
        ray[0] / ray[2] * focal + (viewport.width - 1.0) / 2.0,
        -ray[1] / ray[2] * focal + (viewport.height - 1.0) / 2.0,
    )


class ViewportRayTests(unittest.TestCase):
    def setUp(self):
        self.viewport = RectilinearViewport(
            width=801, height=601, yaw=0.0, pitch=0.0,
            horizontal_fov=math.radians(100.0),
        )
        self.pixels = [
            (200.0, 200.0), (400.0, 200.0), (600.0, 200.0),
            (200.0, 300.0), (400.0, 300.0), (600.0, 300.0),
            (200.0, 400.0), (400.0, 400.0), (600.0, 400.0),
        ]

    def assert_fit(self, rotation):
        matches = []
        for pixel in self.pixels:
            source = pixel_to_world_ray(pixel, self.viewport)
            target = rotate_ray(rotation, source)
            matches.append((pixel, world_ray_to_pixel(target, self.viewport)))
        fit = fit_rotation(pixel_matches_to_world_rays(matches, self.viewport))
        for ray in (
            (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
        ):
            expected = rotate_ray(rotation, ray)
            actual = rotate_ray(fit.rotation_xyzw, ray)
            error = math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(expected, actual)))))
            self.assertLess(error, 1e-7)

    def test_identity_homography_preserves_world_rays(self):
        pairs = homography_to_world_rays(
            (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            RectilinearViewport(
                640, 360, math.radians(37), math.radians(-18),
                math.radians(93), math.radians(11),
            ),
        )
        self.assertEqual(len(pairs), 15)
        for source, target in pairs:
            self.assertEqual(source, target)

    def test_recovers_synthetic_yaw(self):
        self.assert_fit(axis_angle((0.0, 1.0, 0.0), math.radians(4.0)))

    def test_recovers_synthetic_pitch(self):
        # Positive world pitch is a right-handed rotation about -X.
        self.assert_fit(axis_angle((-1.0, 0.0, 0.0), math.radians(4.0)))

    def test_recovers_synthetic_roll(self):
        self.assert_fit(axis_angle((0.0, 0.0, 1.0), math.radians(4.0)))

    def test_viewport_pose_uses_project_world_convention(self):
        center = (400.0, 300.0)
        yawed = pixel_to_world_ray(
            center,
            RectilinearViewport(801, 601, math.pi / 2, 0.0, math.pi / 2),
        )
        pitched = pixel_to_world_ray(
            center,
            RectilinearViewport(801, 601, 0.0, math.pi / 2, math.pi / 2),
        )
        self.assertAlmostEqual(yawed[0], 1.0)
        self.assertAlmostEqual(pitched[1], 1.0)

    def test_public_normalized_interface_axes_and_edges(self):
        center = viewport_normalized_to_world_ray(
            0.5, 0.5, 0.0, 0.0, math.pi / 2.0, 2.0
        )
        right = viewport_normalized_to_world_ray(
            1.0, 0.5, 0.0, 0.0, math.pi / 2.0, 2.0
        )
        top = viewport_normalized_to_world_ray(
            0.5, 0.0, 0.0, 0.0, math.pi / 2.0, 2.0
        )
        self.assertEqual(center, (0.0, 0.0, 1.0))
        self.assertGreater(right[0], 0.0)
        self.assertGreater(top[1], 0.0)
        self.assertAlmostEqual(math.atan2(right[0], right[2]), math.pi / 4.0)
        self.assertAlmostEqual(math.atan2(top[1], top[2]), math.atan(0.5))

    def test_public_normalized_interface_rejects_invalid_values(self):
        arguments = (0.5, 0.5, 0.0, 0.0, math.pi / 2.0, 16.0 / 9.0)
        for index, value in ((0, -0.1), (1, 1.1), (4, 0.0), (5, 0.0)):
            invalid = list(arguments)
            invalid[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                viewport_normalized_to_world_ray(*invalid)

    def test_rejects_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            RectilinearViewport(0, 360, 0.0, 0.0, math.pi / 2)
        with self.assertRaisesRegex(ValueError, "FOV"):
            RectilinearViewport(640, 360, 0.0, 0.0, math.pi)
        with self.assertRaisesRegex(ValueError, "outside"):
            pixel_to_world_ray((-0.6, 0.0), self.viewport)
        with self.assertRaisesRegex(ValueError, "nine finite"):
            homography_to_world_rays([1.0] * 8, self.viewport)
        with self.assertRaisesRegex(ValueError, "no valid"):
            homography_to_world_rays(
                (1.0, 0.0, 5000.0, 0.0, 1.0, 5000.0, 0.0, 0.0, 1.0),
                self.viewport,
            )


if __name__ == "__main__":
    unittest.main()
