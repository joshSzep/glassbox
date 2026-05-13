"""Session-derived rows for the unified operator queue."""

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState
from glassbox.runtime.operator_queue_items import operator_queue_item
from glassbox.runtime.session_query_models import OperatorSessionSummaryView


def build_session_queue_items(
    row: OperatorSessionSummaryView,
) -> list[OperatorQueueItem]:
    """Build queue items derived from one operator session summary row."""

    session_id = str(row.session_id)
    target = NextActionTarget(
        kind=NextActionTargetKind.SESSION,
        target_id=session_id,
        label=f"Session {session_id}",
    )
    items: list[OperatorQueueItem] = []
    if row.pending_approval_id is not None:
        items.append(
            operator_queue_item(
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
                dedupe_key=(
                    f"work:session:{session_id}:approval:{row.pending_approval_id}"
                ),
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
            operator_queue_item(
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
                dedupe_key=(
                    f"work:session:{session_id}:question:{row.pending_question_id}"
                ),
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
            operator_queue_item(
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
            operator_queue_item(
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
            operator_queue_item(
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
            operator_queue_item(
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


__all__ = ["build_session_queue_items"]
