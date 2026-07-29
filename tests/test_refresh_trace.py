import json
import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_refresh import RefreshDetection
from aegis360.refresh_trace import (
    RefreshEvent, build_refresh_trace, dumps_refresh_trace,
)


def detection(identifier, yaw):
    return RefreshDetection(identifier, "person", math.radians(yaw), 0)


class RefreshTraceTests(unittest.TestCase):
    def test_trace_preserves_outcomes_and_never_grants_persistence(self):
        document = build_refresh_trace((
            RefreshEvent(1, "track-1", "person", 0, 0,
                         (detection("p1", 2),)),
            RefreshEvent(2, "track-1", "person", 0, 0,
                         (detection("p1", 2), detection("p2", 3))),
            RefreshEvent(3, "track-1", "person", 0, 0, ()),
        ), source_id="safe-source")
        self.assertEqual(
            [row["outcome"] for row in document["events"]],
            [
                "compatible_not_identity_verified",
                "ambiguous_multiple_compatible",
                "no_compatible_detection",
            ],
        )
        self.assertFalse(any(
            row["editorial_persistence_allowed"]
            for row in document["events"]
        ))
        self.assertEqual(document["geometry_policy"], "strict-v1")
        serialized = dumps_refresh_trace(document)
        json.loads(serialized)
        self.assertNotIn("/Users/", serialized)

    def test_timestamps_must_increase(self):
        event = RefreshEvent(1, "track", "person", 0, 0, ())
        with self.assertRaises(ValueError):
            build_refresh_trace((event, event), source_id="source")

    def test_geometry_policy_is_closed_and_explicit(self):
        event = RefreshEvent(1, "track", "person", 0, 0, ())
        document = build_refresh_trace(
            (event,),
            source_id="source",
            geometry_policy="one-source-pixel-v1",
        )
        self.assertEqual(
            document["geometry_policy"], "one-source-pixel-v1"
        )
        with self.assertRaises(ValueError):
            build_refresh_trace(
                (event,),
                source_id="source",
                geometry_policy="clip-whatever",
            )


if __name__ == "__main__":
    unittest.main()
