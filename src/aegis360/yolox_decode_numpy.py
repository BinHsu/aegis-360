"""NumPy candidate for the frozen dependency-free YOLOX decode contract."""

from __future__ import annotations

from .yolox_decode import DecodedDetection


def decode_yolox_numpy(
    rows,
    *,
    input_size: int = 416,
    strides: tuple[int, ...] = (8, 16, 32),
    confidence_threshold: float = .25,
    nms_iou_threshold: float = .45,
):
    """Decode with vectorized candidate generation and deterministic NMS."""
    import numpy as np

    if (
        input_size <= 0
        or not 0 <= confidence_threshold <= 1
        or not 0 <= nms_iou_threshold <= 1
    ):
        raise ValueError("decode configuration is invalid")
    values = np.asarray(rows)
    expected_rows = sum((input_size // stride) ** 2 for stride in strides)
    if values.shape != (expected_rows, 85):
        raise ValueError("raw row count does not match YOLOX grids")
    if not np.isfinite(values).all():
        raise ValueError("each YOLOX row must contain 85 finite values")

    grids = np.concatenate([
        np.stack(np.meshgrid(
            np.arange(input_size // stride),
            np.arange(input_size // stride),
        ), axis=-1).reshape(-1, 2)
        for stride in strides
    ])
    stride_values = np.concatenate([
        np.full((input_size // stride) ** 2, stride)
        for stride in strides
    ])
    class_ids = np.argmax(values[:, 5:], axis=1)
    indices = np.arange(expected_rows)
    scores = values[:, 4] * values[indices, 5 + class_ids]
    keep = scores >= confidence_threshold
    if not np.any(keep):
        return ()

    source_indices = indices[keep]
    class_ids = class_ids[keep]
    scores = scores[keep]
    selected = values[keep]
    selected_grids = grids[keep]
    selected_strides = stride_values[keep]
    centers = (selected[:, :2] + selected_grids) * selected_strides[:, None]
    sizes = np.exp(selected[:, 2:4]) * selected_strides[:, None]
    boxes = np.concatenate((centers - sizes / 2, sizes), axis=1) / input_size
    order = np.lexsort((source_indices, class_ids, -scores))

    retained = []
    for candidate_index in order:
        candidate_box = boxes[candidate_index]
        candidate_class = int(class_ids[candidate_index])
        suppressed = False
        for prior_index in retained:
            if candidate_class != int(class_ids[prior_index]):
                continue
            left = max(candidate_box[0], boxes[prior_index, 0])
            top = max(candidate_box[1], boxes[prior_index, 1])
            right = min(
                candidate_box[0] + candidate_box[2],
                boxes[prior_index, 0] + boxes[prior_index, 2],
            )
            bottom = min(
                candidate_box[1] + candidate_box[3],
                boxes[prior_index, 1] + boxes[prior_index, 3],
            )
            intersection = max(0.0, right - left) * max(0.0, bottom - top)
            union = (
                candidate_box[2] * candidate_box[3]
                + boxes[prior_index, 2] * boxes[prior_index, 3]
                - intersection
            )
            iou = 0.0 if union <= 0 else intersection / union
            if iou > nms_iou_threshold:
                suppressed = True
                break
        if not suppressed:
            retained.append(candidate_index)

    return tuple(
        DecodedDetection(
            int(class_ids[index]),
            float(scores[index]),
            tuple(float(value) for value in boxes[index]),
            int(source_indices[index]),
        )
        for index in retained
    )
