"""Validation for privacy-safe perception review annotations."""

from __future__ import annotations

from datetime import date
import json
import math
import re
from typing import Any, Mapping

SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
EVENT_LABELS = {
    "action_change", "environment_context", "interaction",
    "obstacle_or_hazard", "person_or_group", "travel_progress",
    "other_visual_event",
}
CANDIDATE_VERDICTS = {"hit", "false_positive", "uncertain"}
REGION_KINDS = {"human", "object", "action", "interaction", "context", "other"}
REVIEWER_KINDS = {"human", "model_assisted"}
MODEL_ASSISTED_LIMITATION = (
    "model-assisted draft; not human ground truth and not valid for human recall conclusions"
)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _keys(value: Mapping[str, Any], required: set[str], path: str) -> None:
    missing, extra = required - value.keys(), value.keys() - required
    if missing:
        raise ValueError(f"{path} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{path} unknown fields: {', '.join(sorted(extra))}")


def _safe_id(value: Any, path: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"{path} must be a non-empty privacy-safe identifier")
    return value


def _number(value: Any, path: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{path} must be finite and within [{low}, {high}]")
    return result


def _unique_ids(rows: list[Any], path: str) -> list[Mapping[str, Any]]:
    output = [_mapping(row, f"{path}[{i}]") for i, row in enumerate(rows)]
    ids = [_safe_id(row.get("id"), f"{path}[{i}].id") for i, row in enumerate(output)]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path} IDs must be unique")
    return output


def validate_review_annotation(document: str | bytes | Mapping[str, Any]) -> None:
    """Validate schema v2; model confidence is intentionally not accepted."""

    root = json.loads(document) if isinstance(document, (str, bytes)) else document
    root = _mapping(root, "root")
    _keys(root, {"schemaVersion", "review", "evidence", "frames", "limitations"}, "root")
    if root["schemaVersion"] != 2:
        raise ValueError("unsupported annotation schemaVersion")

    review = _mapping(root["review"], "review")
    _keys(
        review,
        {
            "reviewerId", "reviewerKind", "reviewedDate",
            "protocolVersion", "interRaterStatus",
        },
        "review",
    )
    _safe_id(review["reviewerId"], "review.reviewerId")
    if (
        not isinstance(review["reviewerKind"], str)
        or review["reviewerKind"] not in REVIEWER_KINDS
    ):
        raise ValueError("review.reviewerKind must be human or model_assisted")
    _safe_id(review["protocolVersion"], "review.protocolVersion")
    try:
        date.fromisoformat(review["reviewedDate"])
    except (TypeError, ValueError):
        raise ValueError("review.reviewedDate must be an ISO YYYY-MM-DD date") from None
    if review["interRaterStatus"] != "not_performed":
        raise ValueError("schema v2 requires interRaterStatus=not_performed")

    evidence = _mapping(root["evidence"], "evidence")
    _keys(evidence, {"sourceId", "evidenceSchemaVersion", "projectionStrategy", "viewportIds"}, "evidence")
    _safe_id(evidence["sourceId"], "evidence.sourceId")
    if evidence["evidenceSchemaVersion"] != 1:
        raise ValueError("evidence.evidenceSchemaVersion must be 1")
    if evidence["projectionStrategy"] != "four_rectilinear_viewports":
        raise ValueError("unsupported evidence.projectionStrategy")
    viewport_ids = [
        _safe_id(value, f"evidence.viewportIds[{i}]")
        for i, value in enumerate(_list(evidence["viewportIds"], "evidence.viewportIds"))
    ]
    if len(viewport_ids) != 4 or len(set(viewport_ids)) != 4:
        raise ValueError("evidence.viewportIds must contain four unique IDs")

    timestamps: set[float] = set()
    for frame_index, frame_value in enumerate(_list(root["frames"], "frames")):
        path = f"frames[{frame_index}]"
        frame = _mapping(frame_value, path)
        _keys(frame, {
            "timestampSeconds", "reviewable", "ordinaryViewerInterest",
            "eventLabels", "candidateReviews", "duplicateGroups",
            "missedImportantRegions",
        }, path)
        timestamp = _number(frame["timestampSeconds"], f"{path}.timestampSeconds", 0, 1e12)
        if timestamp in timestamps:
            raise ValueError("frame timestamps must be unique")
        timestamps.add(timestamp)
        if not isinstance(frame["reviewable"], bool):
            raise ValueError(f"{path}.reviewable must be boolean")
        interest = frame["ordinaryViewerInterest"]
        if isinstance(interest, bool) or not isinstance(interest, int) or interest not in range(4):
            raise ValueError(f"{path}.ordinaryViewerInterest must be integer 0..3")
        labels = _list(frame["eventLabels"], f"{path}.eventLabels")
        if len(labels) != len(set(labels)) or any(label not in EVENT_LABELS for label in labels):
            raise ValueError(f"{path}.eventLabels contains unknown or duplicate labels")
        if not frame["reviewable"] and (interest != 0 or labels):
            raise ValueError(f"{path}: unreviewable frames must use interest 0 and no events")

        candidates = _unique_ids(_list(frame["candidateReviews"], f"{path}.candidateReviews"), f"{path}.candidateReviews")
        candidate_ids: set[str] = set()
        for index, candidate in enumerate(candidates):
            item_path = f"{path}.candidateReviews[{index}]"
            _keys(candidate, {"id", "viewportId", "kind", "verdict"}, item_path)
            candidate_ids.add(candidate["id"])
            if candidate["viewportId"] not in viewport_ids:
                raise ValueError(f"{item_path}.viewportId is not declared by evidence")
            _safe_id(candidate["kind"], f"{item_path}.kind")
            if candidate["verdict"] not in CANDIDATE_VERDICTS:
                raise ValueError(f"{item_path}.verdict is unsupported")

        groups = _unique_ids(_list(frame["duplicateGroups"], f"{path}.duplicateGroups"), f"{path}.duplicateGroups")
        grouped: set[str] = set()
        for index, group in enumerate(groups):
            item_path = f"{path}.duplicateGroups[{index}]"
            _keys(group, {"id", "candidateIds"}, item_path)
            members = _list(group["candidateIds"], f"{item_path}.candidateIds")
            if len(members) < 2 or len(members) != len(set(members)):
                raise ValueError(f"{item_path}.candidateIds must contain unique 2+ IDs")
            if any(member not in candidate_ids for member in members):
                raise ValueError(f"{item_path}.candidateIds references an unknown candidate")
            if grouped.intersection(members):
                raise ValueError(f"{path}: a candidate may appear in only one duplicate group")
            grouped.update(members)

        regions = _unique_ids(_list(frame["missedImportantRegions"], f"{path}.missedImportantRegions"), f"{path}.missedImportantRegions")
        for index, region in enumerate(regions):
            item_path = f"{path}.missedImportantRegions[{index}]"
            _keys(region, {"id", "kind", "yawRadians", "pitchRadians", "horizontalFovRadians"}, item_path)
            if region["kind"] not in REGION_KINDS:
                raise ValueError(f"{item_path}.kind is unsupported")
            _number(region["yawRadians"], f"{item_path}.yawRadians", -math.pi, math.pi)
            _number(region["pitchRadians"], f"{item_path}.pitchRadians", -math.pi / 2, math.pi / 2)
            _number(region["horizontalFovRadians"], f"{item_path}.horizontalFovRadians", 1e-9, math.pi)

    limitations = _list(root["limitations"], "limitations")
    required = "inter-rater agreement has not been measured"
    if required not in limitations:
        raise ValueError(f"limitations must include: {required}")
    if any(not isinstance(item, str) or not item for item in limitations):
        raise ValueError("limitations must contain non-empty strings")
    if (
        review["reviewerKind"] == "model_assisted"
        and MODEL_ASSISTED_LIMITATION not in limitations
    ):
        raise ValueError(
            "model_assisted reviews must state that the draft is not human "
            "ground truth and cannot support human recall conclusions"
        )
