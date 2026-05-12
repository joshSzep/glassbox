"""Runtime aggregation for the unified v16 operator queue."""

from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC

from glassbox.core import MaintenanceCue
from glassbox.core import NextAction
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
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
            *(item for row in rows for item in _session_queue_items(row)),
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


def _session_queue_items(
    row: OperatorSessionSummaryView,
) -> list[OperatorQueueItem]:
    session_id = str(row.session_id)
    target = NextActionTarget(
        kind=NextActionTargetKind.SESSION,
        target_id=session_id,
        label=f"Session {session_id}",
    )
    items: list[OperatorQueueItem] = []
    if row.pending_approval_id is not None:
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:approval",
                family=OperatorQueueFamily.WORK_BLOCKING,
                state=OperatorQueueState.ACTION_NEEDED,
                priority=NextActionPriority.BLOCKED,
                severity=NextActionSeverity.CRITICAL,
                target=target,
                owner_label="Pending approval",
                action_kind=NextActionKind.APPROVE,
                action_title="Resolve pending approval",
                action_summary=row.next_action_summary,
                evidence_kind=NextActionEvidenceKind.EVENT,
                evidence_id=row.pending_approval_id,
                evidence_summary="A pending approval requires an operator decision.",
                dedupe_key=f"work:session:{session_id}:approval:{row.pending_approval_id}",
                dismissal_policy=(
                    OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED
                ),
                blocking=True,
                action_needed=True,
                updated_at=row.updated_at,
            )
        )
    if row.pending_question_id is not None:
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:question",
                family=OperatorQueueFamily.WORK_BLOCKING,
                state=OperatorQueueState.ACTION_NEEDED,
                priority=NextActionPriority.BLOCKED,
                severity=NextActionSeverity.CRITICAL,
                target=target,
                owner_label="Pending question",
                action_kind=NextActionKind.ANSWER,
                action_title="Answer pending question",
                action_summary=row.next_action_summary,
                evidence_kind=NextActionEvidenceKind.EVENT,
                evidence_id=row.pending_question_id,
                evidence_summary="A pending question requires an operator answer.",
                dedupe_key=f"work:session:{session_id}:question:{row.pending_question_id}",
                dismissal_policy=(
                    OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED
                ),
                blocking=True,
                action_needed=True,
                updated_at=row.updated_at,
            )
        )
    if row.status == "failed":
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:failed",
                family=OperatorQueueFamily.WORK_BLOCKING,
                state=OperatorQueueState.BLOCKED,
                priority=NextActionPriority.BLOCKED,
                severity=NextActionSeverity.HIGH,
                target=target,
                owner_label="Failed session",
                action_kind=NextActionKind.RECOVER,
                action_title="Inspect failed session",
                action_summary=row.next_action_summary,
                evidence_kind=NextActionEvidenceKind.EVENT,
                evidence_id=session_id,
                evidence_summary=row.session_failure_message
                or "Session failed before completion.",
                dedupe_key=f"work:session:{session_id}:failed",
                dismissal_policy=(
                    OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED
                ),
                blocking=True,
                action_needed=True,
                updated_at=row.updated_at,
            )
        )
    if row.projection_health.degraded:
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:projection",
                family=OperatorQueueFamily.MAINTENANCE,
                state=OperatorQueueState.DEGRADED,
                priority=NextActionPriority.DEGRADED,
                severity=NextActionSeverity.MEDIUM,
                target=target,
                owner_label="Projection health",
                action_kind=NextActionKind.INSPECT,
                action_title="Inspect stale projection",
                action_summary=row.projection_health.detail
                or "Session projection is degraded.",
                evidence_kind=NextActionEvidenceKind.PROJECTION,
                evidence_id=session_id,
                evidence_summary=row.projection_health.detail
                or "Projection health is degraded.",
                dedupe_key=f"maintenance:session:{session_id}:projection",
                dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
                action_needed=True,
                stale=True,
                updated_at=row.updated_at,
            )
        )
    if row.long_run_status.state in {"stale", "stuck"}:
        is_stuck = row.long_run_status.state == "stuck"
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:long-run",
                family=OperatorQueueFamily.WORK_BLOCKING,
                state=OperatorQueueState.BLOCKED
                if is_stuck
                else OperatorQueueState.STALE,
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.HIGH
                if is_stuck
                else NextActionSeverity.MEDIUM,
                target=target,
                owner_label="Long-running session",
                action_kind=NextActionKind.RECOVER,
                action_title="Inspect long-running session",
                action_summary=row.long_run_status.progress_summary,
                evidence_kind=NextActionEvidenceKind.EVENT,
                evidence_id=session_id,
                evidence_summary=row.long_run_status.stuck_reason
                or row.long_run_status.progress_summary,
                dedupe_key=f"work:session:{session_id}:long-run",
                dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
                blocking=True,
                action_needed=True,
                stale=not is_stuck,
                updated_at=row.updated_at,
            )
        )
    if row.has_active_turn:
        items.append(
            _item(
                item_id=f"queue:session:{session_id}:active",
                family=OperatorQueueFamily.INFORMATIONAL,
                state=OperatorQueueState.ACTIVE,
                priority=NextActionPriority.RECOMMENDED,
                severity=NextActionSeverity.INFO,
                target=target,
                owner_label="Active turn",
                action_kind=NextActionKind.INSPECT,
                action_title="Watch active turn",
                action_summary=row.next_action_summary,
                evidence_kind=NextActionEvidenceKind.EVENT,
                evidence_id=session_id,
                evidence_summary="Session has an active turn in progress.",
                dedupe_key=f"info:session:{session_id}:active",
                dismissal_policy=(
                    OperatorQueueDismissalPolicy.DISMISSIBLE_UNTIL_CHANGED
                ),
                updated_at=row.updated_at,
            )
        )
    return items


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
    return _item(
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


def _item(
    *,
    item_id: str,
    family: OperatorQueueFamily,
    state: OperatorQueueState,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    target: NextActionTarget,
    owner_label: str,
    action_kind: NextActionKind,
    action_title: str,
    action_summary: str,
    evidence_kind: NextActionEvidenceKind,
    evidence_id: str,
    evidence_summary: str,
    dedupe_key: str,
    dismissal_policy: OperatorQueueDismissalPolicy,
    blocking: bool = False,
    action_needed: bool = False,
    stale: bool = False,
    updated_at=None,
) -> OperatorQueueItem:
    action = NextAction(
        action_id=item_id.removeprefix("queue:"),
        title=action_title,
        summary=action_summary,
        kind=action_kind,
        priority=priority,
        severity=severity,
        target=target,
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )
    evidence = NextActionEvidenceRef(
        kind=evidence_kind,
        ref_id=evidence_id,
        summary=evidence_summary,
        freshness="stale" if stale else None,
    )
    return OperatorQueueItem(
        item_id=item_id,
        family=family,
        state=state,
        priority=priority,
        severity=severity,
        target=target,
        owner_surface=NextActionSurface.DASHBOARD,
        owner_label=owner_label,
        safe_next_action=action,
        evidence_summary=OperatorQueueEvidenceSummary(
            summary=evidence_summary,
            supporting_evidence=[] if stale else [evidence],
            stale_evidence=[evidence] if stale else [],
            limitation_count=0,
        ),
        dedupe_key=OperatorQueueDedupeKey(
            scope=OperatorQueueDedupeScope.FAMILY_TARGET,
            key=dedupe_key,
            target=target,
        ),
        dismissal_policy=dismissal_policy,
        action_needed=action_needed,
        blocking=blocking,
        stale=stale,
        updated_at=updated_at,
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
