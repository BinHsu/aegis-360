import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.tile_motion_evidence import TileHomography, fit_tile_motion
from aegis360.viewport_rays import RectilinearViewport, ViewportTile


IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


class TileMotionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.viewport = RectilinearViewport(
            1280, 720, 0.0, 0.0, math.radians(110.0)
        )
        self.tiles = [
            ViewportTile(0, 0, 640, 360),
            ViewportTile(640, 0, 640, 360),
            ViewportTile(0, 360, 640, 360),
            ViewportTile(640, 360, 640, 360),
        ]

    def fit(self, homographies):
        return fit_tile_motion(
            [
                TileHomography(f"tile-{index}", tile, homography)
                for index, (tile, homography)
                in enumerate(zip(self.tiles, homographies))
            ],
            self.viewport,
            homography_columns=5,
            homography_rows=3,
            maximum_disagreement_radians=math.radians(0.5),
            minimum_tiles=3,
            coverage_columns=2,
            coverage_rows=2,
            minimum_covered_cells=3,
        )

    def test_rejects_one_independently_moving_tile(self):
        translated = (
            1.0, 0.0, 80.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        )
        result = self.fit([IDENTITY, IDENTITY, IDENTITY, translated])
        self.assertEqual(result.consensus.state, "selected")
        self.assertEqual(
            result.consensus.selected_tile_ids,
            ("tile-0", "tile-1", "tile-2"),
        )
        self.assertEqual(result.consensus.rejected_tile_ids, ("tile-3",))
        self.assertEqual(len(result.selected_correspondences), 45)

    def test_identity_tiles_preserve_all_spatial_cells(self):
        result = self.fit([IDENTITY] * 4)
        self.assertEqual(result.consensus.state, "selected")
        self.assertEqual(len(result.tile_fits), 4)
        self.assertEqual(
            result.consensus.covered_cell_ids,
            ("r0c0", "r0c1", "r1c0", "r1c1"),
        )
        self.assertEqual(len(result.selected_correspondences), 60)

    def test_duplicate_ids_and_invalid_tile_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            fit_tile_motion(
                [
                    TileHomography("same", self.tiles[0], IDENTITY),
                    TileHomography("same", self.tiles[1], IDENTITY),
                ],
                self.viewport,
                homography_columns=5,
                homography_rows=3,
                maximum_disagreement_radians=0.1,
                minimum_tiles=1,
                coverage_columns=2,
                coverage_rows=2,
                minimum_covered_cells=1,
            )


if __name__ == "__main__":
    unittest.main()
