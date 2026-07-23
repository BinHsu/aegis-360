import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.review_annotations import validate_review_annotation  # noqa: E402


def valid_document():
    return {
        "schemaVersion": 2,
        "review": {
            "reviewerId": "reviewer-01", "reviewedDate": "2026-07-23",
            "reviewerKind": "human",
            "protocolVersion": "perception-review-v2",
            "interRaterStatus": "not_performed",
        },
        "evidence": {
            "sourceId": "old-ghost-road", "evidenceSchemaVersion": 1,
            "projectionStrategy": "four_rectilinear_viewports",
            "viewportIds": ["front", "right", "back", "left"],
        },
        "frames": [{
            "timestampSeconds": 30.0, "reviewable": True,
            "ordinaryViewerInterest": 2, "eventLabels": ["travel_progress"],
            "candidateReviews": [
                {"id": "front:attention:0", "viewportId": "front",
                 "kind": "attention_saliency", "verdict": "hit"},
                {"id": "right:attention:0", "viewportId": "right",
                 "kind": "attention_saliency", "verdict": "hit"},
            ],
            "duplicateGroups": [{
                "id": "duplicate-01",
                "candidateIds": ["front:attention:0", "right:attention:0"],
            }],
            "missedImportantRegions": [{
                "id": "missed-01", "kind": "context",
                "yawRadians": -math.pi, "pitchRadians": 0.1,
                "horizontalFovRadians": 0.4,
            }],
        }],
        "limitations": ["inter-rater agreement has not been measured"],
    }


class ReviewAnnotationTests(unittest.TestCase):
    def test_valid_minimal_review(self):
        validate_review_annotation(json.dumps(valid_document()))

    def test_rejects_v1_instead_of_guessing_reviewer_provenance(self):
        document = valid_document()
        document["schemaVersion"] = 1
        document["review"].pop("reviewerKind")
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            validate_review_annotation(document)

    def test_reviewer_kind_is_closed_enum(self):
        document = valid_document()
        document["review"]["reviewerKind"] = "codex"
        with self.assertRaisesRegex(ValueError, "reviewerKind"):
            validate_review_annotation(document)
        document["review"]["reviewerKind"] = ["human"]
        with self.assertRaisesRegex(ValueError, "reviewerKind"):
            validate_review_annotation(document)

    def test_model_assisted_draft_requires_ground_truth_limitation(self):
        document = valid_document()
        document["review"]["reviewerKind"] = "model_assisted"
        with self.assertRaisesRegex(ValueError, "human ground truth"):
            validate_review_annotation(document)
        document["limitations"].append(
            "model-assisted draft; not human ground truth and not valid for human recall conclusions"
        )
        validate_review_annotation(document)

    def test_confidence_is_not_an_annotation_field(self):
        document = valid_document()
        document["frames"][0]["candidateReviews"][0]["confidence"] = 0.99
        with self.assertRaisesRegex(ValueError, "unknown fields: confidence"):
            validate_review_annotation(document)

    def test_duplicate_group_must_reference_known_candidates(self):
        document = valid_document()
        document["frames"][0]["duplicateGroups"][0]["candidateIds"][1] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown candidate"):
            validate_review_annotation(document)

    def test_missed_region_angles_are_bounded(self):
        document = valid_document()
        document["frames"][0]["missedImportantRegions"][0]["pitchRadians"] = math.pi
        with self.assertRaisesRegex(ValueError, "pitchRadians"):
            validate_review_annotation(document)

    def test_unreviewable_frame_cannot_carry_interest_judgment(self):
        document = valid_document()
        document["frames"][0]["reviewable"] = False
        with self.assertRaisesRegex(ValueError, "unreviewable"):
            validate_review_annotation(document)

    def test_requires_explicit_inter_rater_limitation(self):
        document = valid_document()
        document["limitations"] = []
        with self.assertRaisesRegex(ValueError, "inter-rater agreement"):
            validate_review_annotation(document)

    def test_rejects_path_like_id_and_free_text_field(self):
        document = valid_document()
        document["evidence"]["sourceId"] = "/Users/example/private.mov"
        with self.assertRaisesRegex(ValueError, "privacy-safe"):
            validate_review_annotation(document)
        document = valid_document()
        document["frames"][0]["notes"] = "a named person"
        with self.assertRaisesRegex(ValueError, "unknown fields: notes"):
            validate_review_annotation(document)

    def test_blank_template_has_no_annotations_and_is_incomplete(self):
        template = json.loads(
            (Path(__file__).resolve().parents[1]
             / "benchmarks/review-annotations/template.json").read_text()
        )
        self.assertEqual(template["frames"], [])
        with self.assertRaisesRegex(ValueError, "reviewerId"):
            validate_review_annotation(template)

    def test_candidate_cannot_appear_in_multiple_groups(self):
        document = valid_document()
        extra = copy.deepcopy(document["frames"][0]["duplicateGroups"][0])
        extra["id"] = "duplicate-02"
        document["frames"][0]["duplicateGroups"].append(extra)
        with self.assertRaisesRegex(ValueError, "only one duplicate group"):
            validate_review_annotation(document)


if __name__ == "__main__":
    unittest.main()
