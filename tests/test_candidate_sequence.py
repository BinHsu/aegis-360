import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.candidate_sequence import AssociationConfig, associate_candidate_sequence
from aegis360.interest import INTEREST_SIGNAL_NAMES, InterestConfig, evaluate_interest
from aegis360.perception import (
    AdapterProvenance, FrameSample, PerceptionResult, SignalEvidence,
    SphericalCandidateEvidence,
)


ADAPTER = AdapterProvenance("fixture", "1", "none", "spherical")


def item(identifier, yaw, confidence=0.5):
    return SphericalCandidateEvidence(
        identifier, None, math.radians(yaw), 0.0, math.radians(60), "subject",
        (SignalEvidence("detector_confidence", confidence, confidence, "fixture"),),
        ("fixture",),
    )


def frame(index, candidates):
    return PerceptionResult(
        FrameSample("job:old-ghost-road", float(index), index, 100, 50),
        ADAPTER, tuple(candidates),
    )


class CandidateSequenceTests(unittest.TestCase):
    def test_forward_context_age_is_relative_to_the_sequence(self):
        frames = associate_candidate_sequence((frame(100, ()), frame(101, ())))
        contexts = [
            next(item for item in frame.candidates if item.candidate_id == "context:forward")
            for frame in frames
        ]
        self.assertEqual(
            [(item.observed_frames, item.age_frames) for item in contexts],
            [(1, 1), (2, 2)],
        )

    def test_ids_survive_reordering_and_seam_crossing(self):
        sequence = associate_candidate_sequence((
            frame(0, (item("a", 179), item("b", 30))),
            frame(1, (item("b2", 31), item("a2", -179))),
        ))
        first = {c.source_candidate_id: c.track_id for c in sequence[0].candidates}
        second = {c.source_candidate_id: c.track_id for c in sequence[1].candidates}
        self.assertEqual(first["a"], second["a2"])
        self.assertEqual(first["b"], second["b2"])

    def test_grace_reassociates_then_expires(self):
        config = AssociationConfig(grace_frames=1)
        sequence = associate_candidate_sequence((
            frame(0, (item("a", 10),)),
            frame(1, ()),
            frame(2, (item("a2", 11),)),
        ), config)
        original = next(c for c in sequence[0].candidates if c.track_id)
        grace = next(c for c in sequence[1].candidates if c.track_id)
        resumed = next(c for c in sequence[2].candidates if c.track_id)
        self.assertFalse(grace.observed)
        self.assertEqual(original.track_id, resumed.track_id)

        expired = associate_candidate_sequence((
            frame(0, (item("a", 10),)), frame(1, ()), frame(2, ()),
            frame(3, (item("a3", 10),)),
        ), config)
        self.assertNotEqual(
            next(c for c in expired[0].candidates if c.track_id).track_id,
            next(c for c in expired[3].candidates if c.track_id).track_id,
        )

    def test_forward_context_is_always_available(self):
        sequence = associate_candidate_sequence((frame(0, ()),))
        self.assertEqual([c.candidate_id for c in sequence[0].candidates], ["context:forward"])

    def test_interest_has_only_editorial_signals_not_detector_confidence(self):
        low = associate_candidate_sequence((frame(0, (item("low", 0, 0.01),)),))
        high = associate_candidate_sequence((frame(0, (item("high", 0, 0.99),)),))
        config = InterestConfig(persistence_frames=2)
        low_signals = evaluate_interest(low, config)[0].candidates
        high_signals = evaluate_interest(high, config)[0].candidates
        low_subject = next(c for c in low_signals if c.candidate.track_id)
        high_subject = next(c for c in high_signals if c.candidate.track_id)
        self.assertEqual(tuple(s.name for s in low_subject.signals), INTEREST_SIGNAL_NAMES)
        self.assertEqual(low_subject.signals, high_subject.signals)

    def test_presence_persistence_composition_and_forward_prior(self):
        sequence = associate_candidate_sequence((
            frame(0, (item("a", 0),)), frame(1, (item("a2", 0),)),
        ))
        scored = evaluate_interest(sequence, InterestConfig(persistence_frames=2))
        subject = next(c for c in scored[1].candidates if c.candidate.track_id)
        values = {s.name: s.normalized for s in subject.signals}
        self.assertEqual(values, {
            "presence": 1.0, "persistence": 1.0,
            "composition": 1.0, "forward_prior": 1.0,
        })


if __name__ == "__main__":
    unittest.main()
