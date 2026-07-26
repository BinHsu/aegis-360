"""Past-only reliability ranking for multiview rotation estimates."""

import math

from .so3 import Quaternion
from .view_consensus import select_rotation_consensus


class CausalViewReliability:
    """Rank current views using only disagreement observed on earlier pairs."""

    def __init__(
        self,
        viewport_ids: list[str],
        *,
        selected_viewport_count: int,
        update_alpha: float,
    ):
        ids = tuple(sorted(viewport_ids))
        if not ids:
            raise ValueError("at least one viewport is required")
        if not 1 <= selected_viewport_count <= len(ids):
            raise ValueError("selected viewport count is out of range")
        if not 0.0 < update_alpha <= 1.0:
            raise ValueError("update alpha must be in (0, 1]")
        self._ids = ids
        self._selected_count = selected_viewport_count
        self._alpha = update_alpha
        self._scores = {viewport_id: 0.0 for viewport_id in ids}
        self._observed_pair_count = 0

    @property
    def scores_radians(self) -> dict[str, float]:
        return dict(self._scores)

    def select_for_current_pair(self) -> tuple[str, ...]:
        if self._observed_pair_count == 0:
            return self._ids
        ranked = sorted(
            self._ids,
            key=lambda viewport_id: (
                self._scores[viewport_id], viewport_id
            ),
        )
        return tuple(sorted(ranked[:self._selected_count]))

    def observe_completed_pair(
        self, rotations: dict[str, Quaternion]
    ) -> dict[str, float]:
        if set(rotations) != set(self._ids):
            raise ValueError("completed pair must contain every viewport")
        consensus = select_rotation_consensus(
            rotations,
            maximum_disagreement_radians=math.inf,
            minimum_viewports=1,
        )
        distances = consensus.medoid_distances_radians
        if self._observed_pair_count == 0:
            self._scores = dict(distances)
        else:
            self._scores = {
                viewport_id: (
                    (1.0 - self._alpha) * self._scores[viewport_id]
                    + self._alpha * distances[viewport_id]
                )
                for viewport_id in self._ids
            }
        self._observed_pair_count += 1
        return distances
