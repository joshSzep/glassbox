"""Runtime aggregation for the unified v16 operator queue."""

from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC

from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.runtime.operator_queue_maintenance_items import (
    build_maintenance_queue_items,
)
from glassbox.runtime.operator_queue_runtime_items import build_runtime_queue_items
from glassbox.runtime.operator_queue_session_items import build_session_queue_items
from glassbox.runtime.session_query_models import OperatorQueueCountsView
from glassbox.runtime.session_query_models import OperatorSessionSummaryView
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView

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


def build_operator_queue(
    rows: Sequence[OperatorSessionSummaryView],
    *,
    runtime: WorkspaceRuntimeSummaryView,
    limit: int | None = None,
) -> list[OperatorQueueItem]:
    """Build a deterministic queue from current aggregate-session evidence."""

    items = dedupe_operator_queue_items(
        [
            *(item for row in rows for item in build_session_queue_items(row)),
            *_runtime_queue_items(runtime),
        ]
    )
    sorted_items = sort_operator_queue_items(items)
    return sorted_items if limit is None else sorted_items[:limit]


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


def _runtime_queue_items(
    runtime: WorkspaceRuntimeSummaryView,
) -> list[OperatorQueueItem]:
    if runtime.maintenance_cues:
        return build_maintenance_queue_items(runtime.maintenance_cues)
    return build_runtime_queue_items(runtime)


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


def _family_count(
    items: Sequence[OperatorQueueItem],
    family: OperatorQueueFamily,
) -> int:
    return sum(item.family == family for item in items)
