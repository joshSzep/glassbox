"""Runtime aggregation for the unified v16 operator queue."""

from collections.abc import Sequence

from glassbox.core import OperatorQueueItem
from glassbox.runtime.operator_queue_counts import operator_queue_counts
from glassbox.runtime.operator_queue_maintenance_items import (
    build_maintenance_queue_items,
)
from glassbox.runtime.operator_queue_runtime_items import build_runtime_queue_items
from glassbox.runtime.operator_queue_session_items import build_session_queue_items
from glassbox.runtime.operator_queue_sorting import dedupe_operator_queue_items
from glassbox.runtime.operator_queue_sorting import sort_operator_queue_items
from glassbox.runtime.session_query_models import OperatorSessionSummaryView
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView

__all__ = [
    "build_operator_queue",
    "dedupe_operator_queue_items",
    "operator_queue_counts",
    "sort_operator_queue_items",
]


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


def _runtime_queue_items(
    runtime: WorkspaceRuntimeSummaryView,
) -> list[OperatorQueueItem]:
    if runtime.maintenance_cues:
        return build_maintenance_queue_items(runtime.maintenance_cues)
    return build_runtime_queue_items(runtime)
