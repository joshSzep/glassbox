"""Sorting and dedupe helpers for the unified operator queue."""

from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC

from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import OperatorQueueItem

_PRIORITY_ORDER = {
    NextActionPriority.BLOCKED: 0,
    NextActionPriority.ACTION_NEEDED: 1,
    NextActionPriority.DEGRADED: 2,
    NextActionPriority.RECOMMENDED: 3,
    NextActionPriority.MAINTENANCE_ONLY: 4,
    NextActionPriority.OPTIONAL: 5,
    NextActionPriority.HISTORICAL: 6,
}

_SEVERITY_ORDER = {
    NextActionSeverity.CRITICAL: 0,
    NextActionSeverity.HIGH: 1,
    NextActionSeverity.MEDIUM: 2,
    NextActionSeverity.LOW: 3,
    NextActionSeverity.INFO: 4,
}


def dedupe_operator_queue_items(
    items: Iterable[OperatorQueueItem],
) -> list[OperatorQueueItem]:
    """Merge items with the same dedupe key, keeping the strongest signal."""

    selected: dict[str, OperatorQueueItem] = {}
    for item in items:
        existing = selected.get(item.dedupe_key.key)
        if existing is None or _sort_key(item) < _sort_key(existing):
            selected[item.dedupe_key.key] = item
    return list(selected.values())


def sort_operator_queue_items(
    items: Sequence[OperatorQueueItem],
) -> list[OperatorQueueItem]:
    """Sort by priority, stale/action posture, updated time, and target."""

    return sorted(items, key=_sort_key)


def _sort_key(item: OperatorQueueItem):
    updated = (
        -item.updated_at.replace(tzinfo=UTC).timestamp()
        if item.updated_at is not None
        else 0
    )
    return (
        _PRIORITY_ORDER[item.priority],
        _SEVERITY_ORDER[item.severity],
        not item.action_needed,
        not item.stale,
        updated,
        item.target.kind.value,
        item.target.target_id or "",
        item.item_id,
    )


__all__ = ["dedupe_operator_queue_items", "sort_operator_queue_items"]
