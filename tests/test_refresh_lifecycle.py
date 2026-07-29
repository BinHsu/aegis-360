import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_refresh import RefreshOutcome
from aegis360.refresh_lifecycle import advance_refresh_lifecycle
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


if __name__ == "__main__":
    unittest.main()
