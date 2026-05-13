"""Count helpers for the unified operator queue."""

from collections.abc import Sequence

from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.runtime.session_query_models import OperatorQueueCountsView


def operator_queue_counts(
    items: Sequence[OperatorQueueItem],
) -> OperatorQueueCountsView:
    """Count queue items by v16 queue family."""

    return OperatorQueueCountsView(
        total=len(items),
        work_blocking=_family_count(items, OperatorQueueFamily.WORK_BLOCKING),
        review_blocking=_family_count(items, OperatorQueueFamily.REVIEW_BLOCKING),
        verification_blocking=_family_count(
            items,
            OperatorQueueFamily.VERIFICATION_BLOCKING,
        ),
        maintenance=_family_count(items, OperatorQueueFamily.MAINTENANCE),
        advisory=_family_count(items, OperatorQueueFamily.ADVISORY),
        informational=_family_count(items, OperatorQueueFamily.INFORMATIONAL),
    )


def _family_count(
    items: Sequence[OperatorQueueItem],
    family: OperatorQueueFamily,
) -> int:
    return sum(item.family == family for item in items)


__all__ = ["operator_queue_counts"]
