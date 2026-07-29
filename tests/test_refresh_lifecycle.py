import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_refresh import RefreshOutcome
from aegis360.refresh_lifecycle import (
    advance_refresh_lifecycle, build_refresh_lifecycle_trace,
)
from aegis360.tracking_policy import (
    ObservationKind, TrackEvent, TrackPhase, TrackingPolicy, start_track,
)


class RefreshLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.policy = TrackingPolicy(
            missing_grace_frames=2,
            viewport_exit_grace_frames=1,
            confidence_decay=.5,
        )
        self.initial = start_track(
            "person-1", TrackEvent(0, ObservationKind.OBSERVED, .9)
        )

    def advance(self, state, frame, outcome, confidence=None):
        return advance_refresh_lifecycle(
            state, frame_index=frame, outcome=outcome,
            tracker_confidence=confidence, policy=self.policy,
        )

    def test_detector_miss_enters_grace_then_compatible_recovers(self):
        missing = self.advance(
            self.initial, 1, RefreshOutcome.MISSING
        )
        self.assertEqual(missing.phase, TrackPhase.MISSING_GRACE)
        self.assertEqual(missing.confidence, .45)
        recovered = self.advance(
            missing, 2, RefreshOutcome.COMPATIBLE, .8
        )
        self.assertEqual(recovered.phase, TrackPhase.ACTIVE)
        self.assertEqual(recovered.confidence, .8)

    def test_ambiguous_never_resets_the_track(self):
        ambiguous = self.advance(
            self.initial, 1, RefreshOutcome.AMBIGUOUS
        )
        self.assertEqual(ambiguous.phase, TrackPhase.MISSING_GRACE)
        self.assertEqual(ambiguous.consecutive_missing, 1)

    def test_repeated_misses_terminate_only_after_grace(self):
        state = self.initial
        for frame in (1, 2):
            state = self.advance(state, frame, RefreshOutcome.MISSING)
            self.assertEqual(state.phase, TrackPhase.MISSING_GRACE)
        state = self.advance(state, 3, RefreshOutcome.MISSING)
        self.assertEqual(state.phase, TrackPhase.TERMINATED)

    def test_compatible_requires_real_tracker_confidence(self):
        with self.assertRaises(ValueError):
            self.advance(self.initial, 1, RefreshOutcome.COMPATIBLE)

    def test_trace_materializes_active_grace_active_without_identity_claim(self):
        refresh = {
            "schema_version": "aegis360.detector-refresh-trace.v1",
            "source_id": "fixture",
            "events": [
                self.row(106, "compatible_not_identity_verified"),
                self.row(107, "no_compatible_detection"),
                self.row(108, "compatible_not_identity_verified"),
            ],
        }
        trace = build_refresh_lifecycle_trace(
            refresh, {106.0: .9, 107.0: .8, 108.0: .7},
            policy=self.policy,
        )
        self.assertEqual(
            [row["phase"] for row in trace["states"]],
            ["active", "missing_grace", "active"],
        )
        self.assertEqual(
            [row["confidence"] for row in trace["states"]],
            [.9, .45, .7],
        )
        self.assertTrue(all(
            row["editorial_persistence_allowed"] is False
            and row["identity_verified"] is False
            for row in trace["states"]
        ))
        self.assertEqual(trace["privacy"]["contains_source_path"], False)

    def test_trace_rejects_missing_start_and_missing_compatible_confidence(self):
        with self.assertRaisesRegex(ValueError, "start"):
            build_refresh_lifecycle_trace(
                {
                    "schema_version": "aegis360.detector-refresh-trace.v1",
                    "source_id": "fixture",
                    "events": [self.row(1, "no_compatible_detection")],
                },
                {},
                policy=self.policy,
            )
        with self.assertRaisesRegex(ValueError, "confidence"):
            build_refresh_lifecycle_trace(
                {
                    "schema_version": "aegis360.detector-refresh-trace.v1",
                    "source_id": "fixture",
                    "events": [
                        self.row(1, "compatible_not_identity_verified")
                    ],
                },
                {},
                policy=self.policy,
            )

    def test_trace_terminates_after_bound_and_cannot_revive(self):
        events = [
            self.row(1, "compatible_not_identity_verified"),
            self.row(2, "no_compatible_detection"),
            self.row(3, "no_compatible_detection"),
            self.row(4, "no_compatible_detection"),
        ]
        trace = build_refresh_lifecycle_trace(
            {
                "schema_version": "aegis360.detector-refresh-trace.v1",
                "source_id": "fixture",
                "events": events,
            },
            {1.0: .8},
            policy=self.policy,
        )
        self.assertEqual(
            [row["phase"] for row in trace["states"]],
            ["active", "missing_grace", "missing_grace", "terminated"],
        )
        self.assertEqual(
            trace["states"][-1]["termination_reason"], "missing_timeout"
        )
        with self.assertRaisesRegex(ValueError, "terminated"):
            build_refresh_lifecycle_trace(
                {
                    "schema_version": "aegis360.detector-refresh-trace.v1",
                    "source_id": "fixture",
                    "events": events + [
                        self.row(5, "compatible_not_identity_verified")
                    ],
                },
                {1.0: .8, 5.0: .9},
                policy=self.policy,
            )

    @staticmethod
    def row(timestamp, outcome):
        return {
            "timestamp": timestamp,
            "track_id": "person-1",
            "outcome": outcome,
            "editorial_persistence_allowed": False,
        }


if __name__ == "__main__":
    unittest.main()
