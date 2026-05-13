"""Runtime aggregation for the unified v16 operator queue."""

from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC

from glassbox.core import MaintenanceCue
from glassbox.core import NextAction
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import OperatorQueueDedupeKey
from glassbox.core import OperatorQueueDedupeScope
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueEvidenceSummary
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState
from glassbox.runtime.operator_queue_items import operator_queue_item
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
        return [_maintenance_cue_item(cue) for cue in runtime.maintenance_cues]

    target = NextActionTarget(
        kind=NextActionTargetKind.WORKSPACE,
        target_id=runtime.workspace_root,
        label="Workspace runtime",
    )
    items: list[OperatorQueueItem] = []
    if runtime.background_job_failed_count:
        items.append(
            _runtime_item(
                target,
                runtime,
                item_id="queue:workspace:background-jobs:failed",
                state=OperatorQueueState.BLOCKED,
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.HIGH,
                title="Inspect failed background jobs",
                summary=(
                    f"{runtime.background_job_failed_count} background job(s) failed."
                ),
                dedupe_key="maintenance:workspace:background-jobs:failed",
            )
        )
    if runtime.background_job_retryable_count:
        items.append(
            _runtime_item(
                target,
                runtime,
                item_id="queue:workspace:background-jobs:retryable",
                state=OperatorQueueState.ACTION_NEEDED,
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.MEDIUM,
                title="Inspect retryable background jobs",
                summary=(
                    f"{runtime.background_job_retryable_count} background job(s) "
                    "can be retried."
                ),
                dedupe_key="maintenance:workspace:background-jobs:retryable",
            )
        )
    return items


def _maintenance_cue_item(cue: MaintenanceCue) -> OperatorQueueItem:
    state = _maintenance_cue_state(cue)
    stale = bool(cue.stale_evidence)
    action_needed = cue.priority in {
        NextActionPriority.ACTION_NEEDED,
        NextActionPriority.DEGRADED,
    }
    action = (
        cue.safe_next_actions[0]
        if cue.safe_next_actions
        else NextAction(
            action_id=f"{cue.kind.value}:inspect",
            title=cue.title,
            summary=cue.summary,
            kind=NextActionKind.INSPECT,
            priority=cue.priority,
            severity=cue.severity,
            target=cue.target,
            recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
        )
    )
    limitations = list(cue.limitations)
    if cue.destructive_remediation_note is not None:
        limitations.append(cue.destructive_remediation_note)
    return OperatorQueueItem(
        item_id=f"queue:maintenance:{cue.kind.value}",
        family=OperatorQueueFamily.MAINTENANCE,
        state=state,
        priority=cue.priority,
        severity=cue.severity,
        target=cue.target,
        owner_surface=NextActionSurface.DASHBOARD,
        owner_label=cue.title,
        safe_next_action=action,
        evidence_summary=OperatorQueueEvidenceSummary(
            summary=cue.summary,
            supporting_evidence=cue.supporting_evidence,
            missing_evidence=cue.missing_evidence,
            stale_evidence=cue.stale_evidence,
            limitation_count=len(limitations),
        ),
        dedupe_key=OperatorQueueDedupeKey(
            scope=OperatorQueueDedupeScope.WORKSPACE_SINGLETON,
            key=f"maintenance:{cue.kind.value}",
            target=cue.target,
        ),
        dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
        action_needed=action_needed,
        stale=stale,
        limitations=limitations,
    )


def _maintenance_cue_state(cue: MaintenanceCue) -> OperatorQueueState:
    if cue.priority == NextActionPriority.ACTION_NEEDED:
        return OperatorQueueState.ACTION_NEEDED
    if cue.priority == NextActionPriority.DEGRADED:
        return OperatorQueueState.DEGRADED
    if cue.stale_evidence:
        return OperatorQueueState.STALE
    return OperatorQueueState.WATCHING


def _runtime_item(
    target: NextActionTarget,
    runtime: WorkspaceRuntimeSummaryView,
    *,
    item_id: str,
    state: OperatorQueueState,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    title: str,
    summary: str,
    dedupe_key: str,
) -> OperatorQueueItem:
    return operator_queue_item(
        item_id=item_id,
        family=OperatorQueueFamily.MAINTENANCE,
        state=state,
        priority=priority,
        severity=severity,
        target=target,
        owner_label="Background jobs",
        action_kind=NextActionKind.INSPECT,
        action_title=title,
        action_summary=summary,
        evidence_kind=NextActionEvidenceKind.BACKGROUND_JOB,
        evidence_id=runtime.workspace_root,
        evidence_summary=summary,
        dedupe_key=dedupe_key,
        dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
        action_needed=True,
    )


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
