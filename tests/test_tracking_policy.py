import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.tracking_policy import (  # noqa: E402
    ObservationKind,
    TerminationReason,
    TrackEvent,
    TrackPhase,
    TrackingPolicy,
    advance_track,
    start_track,
)


def observed(frame, confidence=0.8):
    return TrackEvent(frame, ObservationKind.OBSERVED, confidence)


class TrackingPolicyTests(unittest.TestCase):
    def test_missing_grace_decays_then_recovers_from_observation(self):
        policy = TrackingPolicy(missing_grace_frames=2, confidence_decay=0.5)
        state = start_track("job-track:1", observed(0))
        state = advance_track(
            state, TrackEvent(1, ObservationKind.NOT_OBSERVED), policy
        )
        self.assertEqual(state.phase, TrackPhase.MISSING_GRACE)
        self.assertAlmostEqual(state.confidence, 0.4)
        self.assertEqual(state.consecutive_missing, 1)

        state = advance_track(state, observed(2, 0.9), policy)
        self.assertEqual(state.phase, TrackPhase.ACTIVE)
        self.assertEqual(state.consecutive_missing, 0)
        self.assertAlmostEqual(state.confidence, 0.9)

    def test_missing_terminates_only_after_configured_grace(self):
        policy = TrackingPolicy(missing_grace_frames=1)
        state = start_track("job-track:1", observed(5))
        state = advance_track(
            state, TrackEvent(6, ObservationKind.NOT_OBSERVED), policy
        )
        self.assertEqual(state.phase, TrackPhase.MISSING_GRACE)
        state = advance_track(
            state, TrackEvent(7, ObservationKind.NOT_OBSERVED), policy
        )
        self.assertEqual(state.phase, TrackPhase.TERMINATED)
        self.assertEqual(state.termination_reason, TerminationReason.MISSING_TIMEOUT)

    def test_viewport_exit_is_distinct_and_does_not_claim_handoff(self):
        policy = TrackingPolicy(viewport_exit_grace_frames=1)
        state = start_track("job-track:1", observed(0))
        state = advance_track(
            state, TrackEvent(1, ObservationKind.OUTSIDE_VIEWPORT), policy
        )
        self.assertEqual(state.phase, TrackPhase.VIEWPORT_EXIT)
        self.assertEqual(state.consecutive_missing, 0)
        self.assertIsNone(state.termination_reason)

        state = advance_track(
            state, TrackEvent(2, ObservationKind.OUTSIDE_VIEWPORT), policy
        )
        self.assertEqual(state.phase, TrackPhase.TERMINATED)
        self.assertEqual(
            state.termination_reason, TerminationReason.VIEWPORT_EXIT_TIMEOUT
        )

    def test_switching_missing_kinds_resets_the_other_consecutive_counter(self):
        policy = TrackingPolicy(missing_grace_frames=2, viewport_exit_grace_frames=2)
        state = start_track("job-track:1", observed(0))
        state = advance_track(
            state, TrackEvent(1, ObservationKind.NOT_OBSERVED), policy
        )
        state = advance_track(
            state, TrackEvent(2, ObservationKind.OUTSIDE_VIEWPORT), policy
        )
        self.assertEqual(state.consecutive_missing, 0)
        self.assertEqual(state.consecutive_outside, 1)

    def test_zero_grace_terminates_on_first_absence(self):
        state = start_track("job-track:1", observed(0))
        state = advance_track(
            state,
            TrackEvent(1, ObservationKind.NOT_OBSERVED),
            TrackingPolicy(missing_grace_frames=0),
        )
        self.assertEqual(state.phase, TrackPhase.TERMINATED)

    def test_rejects_invalid_events_order_and_terminal_revival(self):
        with self.assertRaises(ValueError):
            TrackEvent(0, ObservationKind.OBSERVED)
        with self.assertRaises(ValueError):
            TrackEvent(0, ObservationKind.NOT_OBSERVED, 0.5)
        with self.assertRaises(ValueError):
            TrackingPolicy(confidence_decay=1.1)

        state = start_track("job-track:1", observed(3))
        with self.assertRaises(ValueError):
            advance_track(state, observed(3), TrackingPolicy())

        terminal = advance_track(
            state,
            TrackEvent(4, ObservationKind.OUTSIDE_VIEWPORT),
            TrackingPolicy(viewport_exit_grace_frames=0),
        )
        with self.assertRaises(ValueError):
            advance_track(terminal, observed(5), TrackingPolicy())


if __name__ == "__main__":
    unittest.main()
