import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.tile_motion_consensus import (
    TileRotation,
    select_tile_motion_consensus,
)


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return (0.0, math.sin(half), 0.0, math.cos(half))


def tile(tile_id, x, y, degrees):
    return TileRotation(tile_id, x, y, yaw(degrees))


class TileMotionConsensusTests(unittest.TestCase):
    def select(self, tiles, minimum_tiles=4, minimum_cells=4):
        return select_tile_motion_consensus(
            tiles,
            maximum_disagreement_radians=math.radians(0.3),
            minimum_tiles=minimum_tiles,
            coverage_columns=2,
            coverage_rows=2,
            minimum_covered_cells=minimum_cells,
        )

    def test_rejects_local_foreground_and_recovers_spanning_background(self):
        result = self.select([
            tile("top-left", 0.15, 0.15, 1.00),
            tile("top-right", 0.85, 0.15, 1.05),
            tile("middle-left", 0.15, 0.50, 0.95),
            tile("middle-right", 0.85, 0.50, 1.02),
            tile("bottom-left", 0.15, 0.85, 1.03),
            tile("bottom-right", 0.85, 0.85, 0.98),
            tile("foreground-a", 0.45, 0.75, 7.0),
            tile("foreground-b", 0.55, 0.75, 7.1),
        ])
        self.assertEqual(result.state, "selected")
        self.assertEqual(
            result.rejected_tile_ids, ("foreground-a", "foreground-b")
        )
        self.assertEqual(
            result.covered_cell_ids, ("r0c0", "r0c1", "r1c0", "r1c1")
        )

    def test_coherent_local_cluster_fails_spatial_coverage(self):
        result = self.select([
            tile("a", 0.05, 0.05, 2.00),
            tile("b", 0.15, 0.05, 2.02),
            tile("c", 0.05, 0.15, 1.98),
            tile("d", 0.15, 0.15, 2.01),
            tile("outlier", 0.85, 0.85, 9.0),
        ])
        self.assertEqual(result.state, "invalid")
        self.assertEqual(
            result.failure_reason, "insufficient_spatial_coverage"
        )

    def test_split_motion_fails_tile_consensus(self):
        result = self.select([
            tile("a", 0.1, 0.1, 0.0),
            tile("b", 0.9, 0.1, 0.1),
            tile("c", 0.1, 0.9, 0.2),
            tile("d", 0.9, 0.9, 5.0),
            tile("e", 0.4, 0.4, 5.1),
            tile("f", 0.6, 0.6, 5.2),
        ])
        self.assertEqual(result.state, "invalid")
        self.assertEqual(result.failure_reason, "insufficient_tile_consensus")

    def test_validation_and_tie_break_are_deterministic(self):
        result = self.select([
            tile("z", 0.1, 0.1, 1.0),
            tile("a", 0.9, 0.9, -1.0),
        ], minimum_tiles=2, minimum_cells=2)
        self.assertEqual(result.medoid_tile_id, "a")
        with self.assertRaises(ValueError):
            self.select([
                tile("same", 0.1, 0.1, 0.0),
                tile("same", 0.9, 0.9, 0.0),
            ])
        with self.assertRaises(ValueError):
            select_tile_motion_consensus(
                [tile("a", 1.1, 0.5, 0.0)],
                maximum_disagreement_radians=0.1,
                minimum_tiles=1,
                coverage_columns=2,
                coverage_rows=2,
                minimum_covered_cells=1,
            )


if __name__ == "__main__":
    unittest.main()
