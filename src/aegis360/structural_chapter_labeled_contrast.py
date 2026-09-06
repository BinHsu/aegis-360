"""Frozen color-independent structural contrast and synthetic episode audit."""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from typing import Iterable, Mapping, Sequence

from .scene_story_semantics import validate_scene_story_semantics


SCHEMA = "aegis360.structural-chapter-labeled-contrast.v1"
CONFIG_SCHEMA = "aegis360.structural-chapter-labeled-contrast-config.v1"
FIXTURE_SCHEMA = "aegis360.structural-episode-fixtures.v1"
PACKET_SOURCE_ID = "old_ghost_road_360.webm"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LIMITATIONS = [
    "the primary ordinal comparison is label-selected and is not held-out evidence",
    "the correlated secondary pair has report-only authority",
    "a passing contrast permits only a separately designed blind replication",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rational(value: object) -> Fraction:
    if (not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}
            or type(value.get("numerator")) is not int
            or type(value.get("denominator")) is not int
            or value["denominator"] <= 0):
        raise ValueError("rational value is invalid")
    return Fraction(value["numerator"], value["denominator"])


def validate_config(config: Mapping[str, object]) -> None:
    top = {"schema_version", "config_id", "source", "acquisition", "descriptor",
           "sample_offsets_seconds", "evaluation_points", "score", "gates",
           "episode_audit"}
    if not isinstance(config, Mapping) or set(config) != top:
        raise ValueError("structural contrast config is invalid")
    acquisition = config.get("acquisition")
    descriptor = config.get("descriptor")
    episode = config.get("episode_audit")
    points = config.get("evaluation_points")
    expected_points = [
        ("event:multi:0005", Fraction(53), "primary", "within_chapter_cut", "action_continuation", "7a693f3cd326c2ef4a03bd6a8e9f393b278e94bdd4b45499a05efb2121498910", "18b2f591f1fa59300c7ff0d879db3672725ef7a2bc7e1086a374bd0f7e5ecdc8", "5fa143b6f1acc6f99a38169f10b37a792019bc7b14d1cdc8b51de45c3eeceb0a"),
        ("event:multi:0008", Fraction(423, 5), "primary", "chapter_boundary", "activity_transition", "df98e7baa4e755686ca494963a92cea1be9a19dc58710aed2bb431ad17ce2452", "3f0452d4f707a6bdb864834dd60d1864d8464efb73cf55bb979a098c13e91f4a", "4047943c16b3806e1b8da77bb5f818a091d768e1b769459a40bc97b69d83bbbf"),
        ("event:multi:0018", Fraction(327, 2), "secondary_correlated", "within_chapter_cut", "action_continuation", "7a693f3cd326c2ef4a03bd6a8e9f393b278e94bdd4b45499a05efb2121498910", "6f4255ca34ab2efb4a4efc6016662adb2981a70d803fff05d8b1ef0e193f018d", "107f6a80b3f9083c5e048368dea7cb39338c2c1e3255914f02da156e6445e11f"),
        ("event:multi:0019", Fraction(842, 5), "secondary_correlated", "chapter_boundary", "activity_transition", "df98e7baa4e755686ca494963a92cea1be9a19dc58710aed2bb431ad17ce2452", "332fdd3d27c90498023d3cd9b0e50a21b767d3e41e98f7580d870e4a17045788", "57c3f29a81e24bf3a26cf754f3564e45587392cb2eedf1a9b77155c7a92af261"),
    ]
    invalid = (
        config.get("schema_version") != CONFIG_SCHEMA
        or config.get("config_id") != "old-ghost-road-structural-chapter-labeled-contrast-v1"
        or config.get("source") != {"id": "old_ghost_road_360", "sha256": "4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc"}
        or acquisition != {"analysis_grid": {"origin_seconds": {"denominator": 1, "numerator": 0}, "rate_fps": 2, "selection": "nearest-grid-point-earlier-tie"}, "ffmpeg_filter_order": ["fps=fps=2:start_time=0:round=near", "scale=160:80:flags=area", "format=gray"], "hash_source_after": True, "hash_source_before": True, "maximum_nominal_to_grid_error_seconds": {"denominator": 4, "numerator": 1}, "pixel_format": "gray8", "threads": 2}
        or not isinstance(descriptor, Mapping)
        or set(descriptor) != {"border_rule", "color_features_forbidden", "component_distance", "component_weights", "discrete_horizontal_alignment", "gradient", "orientation_occupancy", "rounding", "spatial_tiles", "state_center", "vertical_reflect_index_examples", "window_dispersion"}
        or descriptor.get("border_rule") != "horizontal-wrap-vertical-reflect"
        or descriptor.get("color_features_forbidden") is not True
        or descriptor.get("component_distance") != {"combined": "(Dmag+Dori)/2", "magnitude": "sum-32-abs-differences/32", "orientation": "sum-32-(sum-8-abs-differences/2)/32"}
        or descriptor.get("component_weights") != {"mean_magnitude": {"denominator": 2, "numerator": 1}, "orientation_occupancy": {"denominator": 2, "numerator": 1}}
        or descriptor.get("discrete_horizontal_alignment") != {"apply_to": "after-state-center-only-shared-by-both-components", "candidate_tile_shifts": list(range(8)), "selection": "argmin-combined-D-before-center-vs-shifted-after-center", "tie_rule": "smallest-nonnegative-shift"}
        or descriptor.get("gradient") != {"grayscale_range": [0, 255], "gx_kernel": [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], "gy_kernel": [[-1, -2, -1], [0, 0, 0], [1, 2, 1]], "magnitude": "abs-gx-plus-abs-gy-divided-by-2040", "orientation": {"bin_count": 8, "boundary_rule": "lower-inclusive-upper-exclusive", "formula": "atan2(gy,gx)-modulo-pi-into-[0,pi)", "zero_gradient_rule": "zero-weight-all-bins"}}
        or descriptor.get("orientation_occupancy") != "per-tile-magnitude-weighted-bin-mass-normalized-to-sum-one-or-all-zero"
        or descriptor.get("rounding") != {"digits": 8, "stage": "final-recorded-scalars-only-half-even"}
        or descriptor.get("spatial_tiles") != {"columns": 8, "rows": 4}
        or descriptor.get("state_center") != "componentwise-arithmetic-mean-of-four-native-coordinate-frame-descriptors"
        or descriptor.get("vertical_reflect_index_examples") != {"minus_one_maps_to": 1, "height_maps_to": "height-minus-2"}
        or descriptor.get("window_dispersion") != "arithmetic-mean-of-exactly-four-native-coordinate-frame-to-own-state-center-combined-D-no-cyclic-alignment"
        or config.get("sample_offsets_seconds") != [{"denominator": 4, "numerator": n} for n in (-15, -13, -11, -9, 9, 11, 13, 15)]
        or not isinstance(points, list) or len(points) != 4
        or config.get("score") != "max-zero-combined-state-distance-minus-before-dispersion-minus-after-dispersion"
        or config.get("gates") != {"primary": "score-event-multi-0008-strictly-greater-than-score-event-multi-0005-after-eight-decimal-rounding", "secondary": "report-order-only-no-pass-authority", "success_authority": "blind-replication-design-only"}
        or episode != {"fixture_sha256": "3cd1cc5360c61035adac8c15c7cfda103d0ced31c34cc712d702ff271eee4913", "maximum_entry_exit_separation_seconds": 60, "middle_consistency_ratio": {"denominator": 2, "numerator": 1}, "outer_return_ratio": {"denominator": 2, "numerator": 1}, "pairing": "chronological-entry; eligible-exit-minimizes-rA-plus-rB-then-earliest; rA=D(A0,A1)/min(entry,exit); rB=D(B0,B1)/min(entry,exit); require-entry-and-exit-positive-separation-at-most-60-rA-at-most-half-rB-at-most-half; chosen-pairs-disjoint", "schema_version": FIXTURE_SCHEMA, "synthetic_only": True, "zero_transition_rule": "not-pairable"}
    )
    if invalid:
        raise ValueError("structural contrast config is invalid")
    hashes = set()
    for point, expected in zip(points, expected_points):
        event_id, center, group, role, function, label_sha, packet_sha, semantic_sha = expected
        if (not isinstance(point, Mapping)
                or set(point) != {"center_source_time", "event_id", "expected", "label_config_sha256", "packet_sha256", "semantic_evidence_sha256", "set"}
                or point["event_id"] != event_id or _rational(point["center_source_time"]) != center
                or point["set"] != group
                or point["expected"] != {"change_type": "hard_cut", "narrative_function": function, "status": "observed", "structural_role": role}
                or (point["label_config_sha256"], point["packet_sha256"], point["semantic_evidence_sha256"]) != (label_sha, packet_sha, semantic_sha)
                or any(not isinstance(point[k], str) or SHA256.fullmatch(point[k]) is None for k in ("label_config_sha256", "packet_sha256", "semantic_evidence_sha256"))):
            raise ValueError("structural contrast evaluation point is invalid")
        hashes.add((point["packet_sha256"], point["semantic_evidence_sha256"]))
    if len(hashes) != 4:
        raise ValueError("structural contrast evidence hashes are not unique")


def validate_evidence(config: Mapping[str, object], bindings: Mapping[str, tuple[bytes, Mapping[str, object], bytes, Mapping[str, object], bytes, Mapping[str, object]]]) -> None:
    validate_config(config)
    if set(bindings) != {p["event_id"] for p in config["evaluation_points"]}:
        raise ValueError("exactly four evidence bindings are required")
    for point in config["evaluation_points"]:
        packet_bytes, packet, label_bytes, label, semantics_bytes, semantics = bindings[point["event_id"]]
        if (sha256_bytes(packet_bytes) != point["packet_sha256"]
                or sha256_bytes(label_bytes) != point["label_config_sha256"]
                or sha256_bytes(semantics_bytes) != point["semantic_evidence_sha256"]):
            raise ValueError("evidence checksum does not match frozen binding")
        if packet.get("schema_version") != "aegis360.scene-story-review-packet.v1" or packet.get("event_id") != point["event_id"] or packet.get("source_id") != PACKET_SOURCE_ID:
            raise ValueError("review packet content does not match frozen binding")
        validate_scene_story_semantics(semantics, label, packet, config_sha256=point["label_config_sha256"], packet_sha256=point["packet_sha256"])
        expected = point["expected"]
        if any(semantics["evidence"].get(k) != v for k, v in expected.items()):
            raise ValueError("semantic evidence content does not match frozen label")


def _reflect101(y: int, height: int) -> int:
    if y < 0:
        return -y
    if y >= height:
        return 2 * height - 2 - y
    return y


def frame_descriptor(frame: bytes, width: int = 160, height: int = 80) -> tuple[list[float], list[list[float]]]:
    if len(frame) != width * height or width != 160 or height != 80:
        raise ValueError("decoded gray frame has an invalid byte count")
    mag_sum = [0.0] * 32
    ori_sum = [[0.0] * 8 for _ in range(32)]
    count = (width // 8) * (height // 4)
    kx = ((-1, 0, 1), (-2, 0, 2), (-1, 0, 1))
    ky = ((-1, -2, -1), (0, 0, 0), (1, 2, 1))
    for y in range(height):
        tile_y = y // (height // 4)
        for x in range(width):
            gx = gy = 0
            for j in range(3):
                yy = _reflect101(y + j - 1, height)
                row = yy * width
                for i in range(3):
                    value = frame[row + ((x + i - 1) % width)]
                    gx += kx[j][i] * value
                    gy += ky[j][i] * value
            magnitude = (abs(gx) + abs(gy)) / 2040.0
            tile = tile_y * 8 + x // (width // 8)
            mag_sum[tile] += magnitude
            if magnitude:
                angle = math.atan2(gy, gx) % math.pi
                orientation_bin = min(7, int(angle * 8 / math.pi))
                ori_sum[tile][orientation_bin] += magnitude
    magnitudes = [value / count for value in mag_sum]
    orientations = []
    for values in ori_sum:
        total = sum(values)
        orientations.append([value / total for value in values] if total else [0.0] * 8)
    return magnitudes, orientations


def _center(descriptors):
    return ([sum(d[0][i] for d in descriptors) / 4 for i in range(32)],
            [[sum(d[1][i][b] for d in descriptors) / 4 for b in range(8)] for i in range(32)])


def _distance(left, right, shift: int = 0) -> tuple[float, float, float]:
    mag = ori = 0.0
    for row in range(4):
        for col in range(8):
            li = row * 8 + col
            ri = row * 8 + ((col + shift) % 8)
            mag += abs(left[0][li] - right[0][ri])
            ori += sum(abs(a - b) for a, b in zip(left[1][li], right[1][ri])) / 2
    dmag, dori = mag / 32, ori / 32
    return dmag, dori, (dmag + dori) / 2


def _half_even(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN))


def evaluation_metrics(frames: Sequence[bytes]) -> dict[str, object]:
    if len(frames) != 8:
        raise ValueError("evaluation requires exactly eight frames")
    descriptors = [frame_descriptor(frame) for frame in frames]
    before, after = _center(descriptors[:4]), _center(descriptors[4:])
    choices = [(*_distance(before, after, shift), shift) for shift in range(8)]
    dmag, dori, state, shift = min(choices, key=lambda row: (row[2], row[3]))
    before_dispersion = sum(_distance(item, before)[2] for item in descriptors[:4]) / 4
    after_dispersion = sum(_distance(item, after)[2] for item in descriptors[4:]) / 4
    values = {"magnitude_distance": dmag, "orientation_distance": dori,
              "state_distance": state, "before_dispersion": before_dispersion,
              "after_dispersion": after_dispersion,
              "score": max(0.0, state - before_dispersion - after_dispersion)}
    return {**{key: _half_even(value) for key, value in values.items()}, "selected_horizontal_tile_shift": shift}


def _nearest_grid_index(time: Fraction) -> int:
    scaled = time * 2
    floor = scaled.numerator // scaled.denominator
    remainder = scaled - floor
    return floor if remainder <= Fraction(1, 2) else floor + 1


def sample_plan(config: Mapping[str, object]) -> dict[str, list[dict[str, object]]]:
    validate_config(config)
    result = {}
    maximum = _rational(config["acquisition"]["maximum_nominal_to_grid_error_seconds"])
    offsets = [_rational(value) for value in config["sample_offsets_seconds"]]
    for point in config["evaluation_points"]:
        center = _rational(point["center_source_time"])
        rows = []
        used = set()
        for offset in offsets:
            nominal = center + offset
            index = _nearest_grid_index(nominal)
            selected = Fraction(index, 2)
            if abs(selected - nominal) > maximum or index in used or (offset < 0) != (selected < center):
                raise ValueError("sample mapping violates frozen grid policy")
            used.add(index)
            rows.append({"frame_index": index, "nominal_time": {"numerator": nominal.numerator, "denominator": nominal.denominator}, "grid_time": {"numerator": selected.numerator, "denominator": selected.denominator}})
        result[point["event_id"]] = rows
    return result


def run_episode_audit(fixtures: Mapping[str, object]) -> list[dict[str, object]]:
    if not isinstance(fixtures, Mapping) or set(fixtures) != {"schema_version", "distance", "cases"} or fixtures.get("schema_version") != FIXTURE_SCHEMA or fixtures.get("distance") != "absolute-difference-of-exact-rational-scalars" or not isinstance(fixtures.get("cases"), list):
        raise ValueError("structural episode fixtures are invalid")
    results = []
    for case in fixtures["cases"]:
        if not isinstance(case, Mapping) or set(case) != {"case_id", "candidates", "expected_pairs"} or not isinstance(case["case_id"], str) or not isinstance(case["candidates"], list):
            raise ValueError("structural episode fixture case is invalid")
        candidates = []
        ids = set()
        last_time = None
        for raw in case["candidates"]:
            if not isinstance(raw, Mapping) or set(raw) != {"candidate_id", "time_seconds", "before", "after"} or not isinstance(raw["candidate_id"], str) or raw["candidate_id"] in ids or type(raw["time_seconds"]) is not int or (last_time is not None and raw["time_seconds"] <= last_time):
                raise ValueError("structural episode fixture candidate is invalid")
            ids.add(raw["candidate_id"]); last_time = raw["time_seconds"]
            candidates.append((raw["candidate_id"], raw["time_seconds"], _rational(raw["before"]), _rational(raw["after"])))
        used = set(); pairs = []
        for i, entry_item in enumerate(candidates):
            if i in used:
                continue
            eid, etime, a0, b0 = entry_item
            eligible = []
            for j in range(i + 1, len(candidates)):
                if j in used:
                    continue
                xid, xtime, b1, a1 = candidates[j]
                entry, exit_distance = abs(a0 - b0), abs(b1 - a1)
                if entry == 0 or exit_distance == 0 or xtime - etime > 60:
                    continue
                denominator = min(entry, exit_distance)
                ra, rb = abs(a0 - a1) / denominator, abs(b0 - b1) / denominator
                if ra <= Fraction(1, 2) and rb <= Fraction(1, 2):
                    eligible.append((ra + rb, xtime, j, xid))
            if eligible:
                _, _, j, xid = min(eligible)
                used.update((i, j)); pairs.append([eid, xid])
        if pairs != case["expected_pairs"]:
            raise ValueError("structural episode fixture expected result mismatch")
        results.append({"case_id": case["case_id"], "pairs": pairs, "passed": True})
    if len(results) != 8:
        raise ValueError("structural episode fixture count is invalid")
    return results


def build_artifact(*, config: Mapping[str, object], config_sha256: str,
                   fixture_sha256: str, source_sha256_before: str,
                   source_sha256_after: str, frame_count: int,
                   selected_frames: Mapping[int, bytes], episode_results) -> dict[str, object]:
    validate_config(config)
    expected_hashes = (config["source"]["sha256"], config["episode_audit"]["fixture_sha256"])
    if (not all(isinstance(v, str) and SHA256.fullmatch(v) for v in (config_sha256, fixture_sha256, source_sha256_before, source_sha256_after))
            or source_sha256_before != source_sha256_after or source_sha256_before != expected_hashes[0]
            or fixture_sha256 != expected_hashes[1] or type(frame_count) is not int or frame_count <= 0):
        raise ValueError("structural contrast lineage is invalid")
    plan = sample_plan(config)
    evaluations = []
    for point in config["evaluation_points"]:
        rows = plan[point["event_id"]]
        if any(row["frame_index"] >= frame_count or row["frame_index"] not in selected_frames for row in rows):
            raise ValueError("decoded source is missing a required sample")
        metrics = evaluation_metrics([selected_frames[row["frame_index"]] for row in rows])
        evaluations.append({"event_id": point["event_id"], "set": point["set"],
                            "evidence_lineage": {"packet_sha256": point["packet_sha256"], "label_config_sha256": point["label_config_sha256"], "semantic_evidence_sha256": point["semantic_evidence_sha256"]},
                            "expected": point["expected"], "samples": rows,
                            "metrics": metrics})
    scores = {row["event_id"]: row["metrics"]["score"] for row in evaluations}
    passed = scores["event:multi:0008"] > scores["event:multi:0005"]
    return {"schema_version": SCHEMA, "source_id": config["source"]["id"],
            "inputs": {"config_sha256": config_sha256,
                       "fixture_sha256": fixture_sha256,
                       "source_sha256_before": source_sha256_before,
                       "source_sha256_after": source_sha256_after},
            "acquisition": {"frame_count": frame_count, "rate_fps": 2, "width": 160, "height": 80, "pixel_format": "gray8", "grid_rule": "source_seconds=n/2"},
            "evaluations": evaluations, "episode_audit": episode_results,
            "gate": {"primary_passed": passed, "primary_authority": "blind-replication-design-only" if passed else "hypothesis-rejected", "secondary_authority": "report-only"},
            "authority": {"story_boundary": False, "camera_choice": False, "render": False},
            "privacy": {"contains_source_path": False, "contains_pixels": False, "contains_audio": False},
            "limitations": LIMITATIONS}


def validate_artifact(document: Mapping[str, object], **kwargs) -> None:
    if document != build_artifact(**kwargs):
        raise ValueError("structural contrast artifact must exactly derive from inputs")
