import math
import unittest

from aegis360.framing import FramingSafetyConfig, safe_horizontal_fovs


class FramingSafetyTests(unittest.TestCase):
    def test_minimum_padding_and_zoom_in_delta_are_independent_guards(self):
        config = FramingSafetyConfig(
            minimum_h_fov=math.radians(110),
            candidate_extent_padding=math.radians(10),
            max_zoom_in_change=math.radians(15),
        )
        guarded = safe_horizontal_fovs(
            map(math.radians, (130, 80, 60, 150)), config
        )
        self.assertEqual(
            [round(math.degrees(value)) for value in guarded],
            [150, 135, 120, 170],
        )

    def test_invalid_config_and_extent_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "minimum horizontal FOV"):
            FramingSafetyConfig(minimum_h_fov=math.pi)
        with self.assertRaisesRegex(ValueError, "padding"):
            FramingSafetyConfig(candidate_extent_padding=-0.1)
        with self.assertRaisesRegex(ValueError, "candidate horizontal extent"):
            safe_horizontal_fovs((0.0,), FramingSafetyConfig())


if __name__ == "__main__":
    unittest.main()
