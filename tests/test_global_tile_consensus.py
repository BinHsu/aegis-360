import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.global_tile_consensus import (
    SphericalTileRotation,
    select_global_tile_consensus,
)


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return (0.0, math.sin(half), 0.0, math.cos(half))


def group(prefix, viewports, count, degrees):
    return [
        SphericalTileRotation(
            f"{prefix}-{index:02d}", viewports[index % len(viewports)],
            yaw(degrees + (index % 3 - 1) * 0.03),
        )
        for index in range(count)
    ]


class GlobalTileConsensusTests(unittest.TestCase):
    def select(self, tiles):
        return select_global_tile_consensus(
            tiles,
            maximum_disagreement_radians=math.radians(0.5),
            minimum_tiles=13,
            minimum_viewports=4,
        )

    def test_strict_spanning_majority_rejects_local_motion(self):
        background = group(
            "background", ["front", "left", "right", "up", "down"], 15, 1.0
        )
        foreground = group(
            "foreground", ["front", "down", "right"], 9, 7.0
        )
        result = self.select(background + foreground)
        self.assertEqual(result.state, "selected")
        self.assertEqual(len(result.selected_tile_ids), 15)
        self.assertEqual(len(result.rejected_tile_ids), 9)
        self.assertEqual(len(result.selected_viewport_ids), 5)

    def test_thirteen_tiles_from_three_views_fail_coverage(self):
        result = self.select(
            group("local", ["front", "right", "down"], 13, 2.0)
            + group("other", ["left", "up", "back"], 11, 8.0)
        )
        self.assertEqual(result.state, "invalid")
        self.assertEqual(
            result.failure_reason, "insufficient_global_viewport_coverage"
        )

    def test_even_split_fails_strict_majority(self):
        result = self.select(
            group("a", ["front", "left", "up", "down"], 12, 0.0)
            + group("b", ["back", "right", "up", "down"], 12, 6.0)
        )
        self.assertEqual(result.state, "invalid")
        self.assertEqual(
            result.failure_reason, "insufficient_global_tile_consensus"
        )


if __name__ == "__main__":
    unittest.main()
