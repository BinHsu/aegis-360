import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.so3 import fit_rotation, rotate_ray


def axis_angle(axis, angle):
    scale = math.sin(angle / 2.0)
    return (axis[0] * scale, axis[1] * scale, axis[2] * scale, math.cos(angle / 2.0))


def multiply(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


RAYS = [
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (-1.0, 0.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, -1.0),
    (math.sqrt(0.5), math.sqrt(0.5), 0.0),
    (0.0, math.sqrt(0.5), math.sqrt(0.5)),
]


class RotationFitTests(unittest.TestCase):
    def assert_rotation(self, expected, fit, tolerance=5e-8):
        for ray in RAYS:
            wanted = rotate_ray(expected, ray)
            actual = rotate_ray(fit.rotation_xyzw, ray)
            error = math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(wanted, actual)))))
            self.assertLess(error, tolerance)

    def fit_exact(self, rotation):
        return fit_rotation((ray, rotate_ray(rotation, ray)) for ray in RAYS)

    def test_yaw_pitch_and_roll(self):
        # +yaw is a right-handed rotation about +Y: +Z moves toward +X.
        fixtures = [
            axis_angle((0.0, 1.0, 0.0), math.radians(37)),
            axis_angle((1.0, 0.0, 0.0), math.radians(-23)),
            axis_angle((0.0, 0.0, 1.0), math.radians(61)),
        ]
        for rotation in fixtures:
            with self.subTest(rotation=rotation):
                fit = self.fit_exact(rotation)
                self.assert_rotation(rotation, fit)
                self.assertAlmostEqual(fit.inlier_ratio, 1.0)
                self.assertGreater(fit.confidence, 0.99)
                self.assertLess(fit.residual_radians, 1e-7)

    def test_composed_rotation(self):
        rotation = multiply(
            axis_angle((0.0, 1.0, 0.0), math.radians(28)),
            multiply(
                axis_angle((1.0, 0.0, 0.0), math.radians(-17)),
                axis_angle((0.0, 0.0, 1.0), math.radians(12)),
            ),
        )
        self.assert_rotation(rotation, self.fit_exact(rotation))

    def test_robust_to_outliers(self):
        rotation = multiply(
            axis_angle((0.0, 1.0, 0.0), math.radians(41)),
            axis_angle((1.0, 0.0, 0.0), math.radians(-11)),
        )
        pairs = [(ray, rotate_ray(rotation, ray)) for ray in RAYS]
        pairs.extend([
            ((math.sqrt(0.5), 0.0, math.sqrt(0.5)), (0.0, -1.0, 0.0)),
            ((-math.sqrt(0.5), 0.0, math.sqrt(0.5)), (1.0, 0.0, 0.0)),
        ])
        fit = fit_rotation(pairs)
        self.assert_rotation(rotation, fit, tolerance=1e-7)
        self.assertEqual(fit.inlier_count, len(RAYS))
        self.assertAlmostEqual(fit.inlier_ratio, 0.8)
        self.assertGreater(fit.confidence, 0.75)

    def test_reports_finite_residual_for_noisy_inliers(self):
        rotation = axis_angle((0.0, 1.0, 0.0), math.radians(19))
        pairs = []
        for index, ray in enumerate(RAYS):
            target = rotate_ray(rotation, ray)
            delta = (index - 3.5) * 0.0002
            perturbed = (target[0] + delta, target[1] - delta / 2.0, target[2])
            norm = math.sqrt(sum(value * value for value in perturbed))
            pairs.append((ray, tuple(value / norm for value in perturbed)))
        fit = fit_rotation(pairs)
        self.assertEqual(fit.inlier_count, len(RAYS))
        self.assertGreater(fit.residual_radians, 0.0)
        self.assertLess(fit.residual_radians, math.radians(0.1))
        self.assertGreater(fit.confidence, 0.95)

    def test_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            fit_rotation([((1.0, 0.0, 0.0), (1.0, 0.0, 0.0))])
        with self.assertRaisesRegex(ValueError, "unit length"):
            fit_rotation([
                ((2.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
                ((0.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
            ])
        with self.assertRaisesRegex(ValueError, "angular diversity"):
            fit_rotation([
                ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
            ])


if __name__ == "__main__":
    unittest.main()
