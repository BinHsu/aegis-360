import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.candidate_sequence import (
    AssociationConfig, AssociationProvenance, associate_candidate_sequence,
)
from aegis360.interest import INTEREST_SIGNAL_NAMES, InterestConfig, evaluate_interest
from aegis360.perception import (
    AdapterProvenance, FrameSample, PerceptionResult, SignalEvidence,
    SphericalCandidateEvidence,
)


ADAPTER = AdapterProvenance("fixture", "1", "none", "spherical")


def item(identifier, yaw, confidence=0.5, kind="subject", track_id=None):
    return SphericalCandidateEvidence(
        identifier, track_id, math.radians(yaw), 0.0, math.radians(60), kind,
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
            frame(0, (item("a", 0, kind="human"),)),
            frame(1, (item("a2", 0, kind="human"),)),
        ))
        scored = evaluate_interest(sequence, InterestConfig(persistence_frames=2))
        subject = next(c for c in scored[1].candidates if c.candidate.track_id)
        values = {s.name: s.normalized for s in subject.signals}
        self.assertEqual(values, {
            "presence": 1.0, "persistence": 1.0,
            "composition": 1.0, "forward_prior": 1.0,
        })

    def test_forward_context_is_a_fallback_not_a_detected_persistent_subject(self):
        sequence = associate_candidate_sequence((frame(100, ()), frame(101, ())))
        scored = evaluate_interest(sequence, InterestConfig(persistence_frames=2))
        for scored_frame in scored:
            context = next(
                item
                for item in scored_frame.candidates
                if item.candidate.candidate_id == "context:forward"
            )
            values = {signal.name: signal.normalized for signal in context.signals}
            self.assertEqual(values["presence"], 0.0)
            self.assertEqual(values["persistence"], 0.0)
            self.assertEqual(values["composition"], 1.0)
            self.assertEqual(values["forward_prior"], 1.0)

    def test_saliency_nearest_neighbor_does_not_gain_editorial_persistence(self):
        for kind in ("attention_saliency", "objectness_saliency"):
            with self.subTest(kind=kind):
                sequence = associate_candidate_sequence((
                    frame(0, (item("a", 0, kind=kind),)),
                    frame(1, (item("b", 1, kind=kind),)),
                ))
                candidate = next(c for c in sequence[1].candidates if c.track_id)
                self.assertEqual(candidate.observed_frames, 2)
                self.assertEqual(
                    candidate.association_provenance,
                    AssociationProvenance.GEOMETRIC_ONLY,
                )
                signals = {
                    signal.name: signal
                    for signal in next(
                        item
                        for item in evaluate_interest(sequence)[1].candidates
                        if item.candidate.track_id
                    ).signals
                }
                self.assertEqual(signals["persistence"].raw, 0.0)
                self.assertEqual(signals["persistence"].normalized, 0.0)

    def test_explicit_tracker_identity_grants_persistence_without_confidence(self):
        sequence = associate_candidate_sequence((
            frame(0, (item("a", 0, 0.01, "objectness_saliency", "subject-7"),)),
            frame(1, (item("b", 80, 0.99, "objectness_saliency", "subject-7"),)),
        ))
        candidate = next(c for c in sequence[1].candidates if c.track_id)
        self.assertEqual(candidate.observed_frames, 2)
        self.assertEqual(
            candidate.association_provenance,
            AssociationProvenance.TRACKER_IDENTITY,
        )
        signals = {
            signal.name: signal
            for signal in next(
                item
                for item in evaluate_interest(
                    sequence, InterestConfig(persistence_frames=2)
                )[1].candidates
                if item.candidate.track_id
            ).signals
        }
        self.assertEqual(signals["persistence"].normalized, 1.0)

    def test_explicit_tracker_ids_are_not_nearest_neighbor_swapped(self):
        sequence = associate_candidate_sequence((
            frame(0, (
                item("left", -10, track_id="left"),
                item("right", 10, track_id="right"),
            )),
            frame(1, (
                item("left-crossed", 10, track_id="left"),
                item("right-crossed", -10, track_id="right"),
            )),
        ))
        first = {c.source_candidate_id: c.track_id for c in sequence[0].candidates}
        second = {c.source_candidate_id: c.track_id for c in sequence[1].candidates}
        self.assertEqual(first["left"], second["left-crossed"])
        self.assertEqual(first["right"], second["right-crossed"])


if __name__ == "__main__":
    unittest.main()
