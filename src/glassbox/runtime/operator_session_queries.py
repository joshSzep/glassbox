"""Operator-console queue and priority aggregation for session summaries."""

from collections.abc import Sequence
from datetime import UTC

from glassbox.runtime.session_query_models import OPERATOR_QUEUE_ACTION_NEEDED
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_ACTIVE
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_ALL
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_APPROVALS
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_DEGRADED
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_FAILURES
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_HISTORICAL
from glassbox.runtime.session_query_models import OPERATOR_QUEUE_QUESTIONS
from glassbox.runtime.session_query_models import OPERATOR_SORT_UPDATED_AT
from glassbox.runtime.session_query_models import OperatorQueueName
from glassbox.runtime.session_query_models import OperatorSessionSummaryView
from glassbox.runtime.session_query_models import OperatorSortName
from glassbox.runtime.session_query_models import ProjectionHealthCountsView
from glassbox.runtime.session_query_models import SessionQueueCountsView
from glassbox.runtime.session_query_models import SessionSummaryView

_RECOVERY_ACTION_STATES = {"incomplete", "recoverable", "abandoned", "non_resumable"}


def build_operator_session_summary(
    summary: SessionSummaryView,
) -> OperatorSessionSummaryView:
    has_active_turn = (
        summary.status == "running"
        and summary.next_action_summary == "Wait for the current turn to finish"
    )
    live_actionable = summary.status in {
        "running",
        "awaiting_approval",
        "awaiting_user_input",
    }
    historical_only = not live_actionable
    priority_bucket, priority_rank = operator_priority(summary, has_active_turn)
    action_needed = bool(
        summary.pending_approval_id is not None
        or summary.pending_question_id is not None
        or summary.status == "failed"
        or summary.projection_health.degraded
        or _has_provider_recovery_attention(summary)
        or _has_recovery_action(summary)
        or summary.long_run_status.state in {"stale", "stuck"}
    )
    queue_memberships = operator_queue_memberships(
        summary,
        live_actionable=live_actionable,
        historical_only=historical_only,
        action_needed=action_needed,
    )

    payload = summary.model_dump()
    payload.update(
        {
            "queue_memberships": queue_memberships,
            "priority_bucket": priority_bucket,
            "priority_rank": priority_rank,
            "action_needed": action_needed,
            "live_actionable": live_actionable,
            "historical_only": historical_only,
            "has_active_turn": has_active_turn,
        }
    )
    return OperatorSessionSummaryView.model_validate(payload)


def operator_priority(
    summary: SessionSummaryView,
    has_active_turn: bool,
) -> tuple[str, int]:
    if summary.pending_approval_id is not None:
        return "approvals", 0
    if summary.pending_question_id is not None:
        return "questions", 1
    if summary.status == "failed":
        return "failures", 2
    if summary.projection_health.degraded:
        return "degraded", 3
    if _has_provider_recovery_attention(summary):
        return "provider_recovery", 3
    if _has_recovery_action(summary):
        return "recovery", 3
    if summary.long_run_status.state == "stuck":
        return "stuck", 3
    if summary.long_run_status.state == "stale":
        return "stale", 3
    if has_active_turn:
        return "running", 4
    if summary.status == "running":
        return "idle_running", 5
    return "historical", 6


def matches_operator_queue(
    row: OperatorSessionSummaryView,
    queue: OperatorQueueName | None,
) -> bool:
    if queue is None or queue == OPERATOR_QUEUE_ALL:
        return True
    return queue in row.queue_memberships


def matches_operator_status(
    row: OperatorSessionSummaryView,
    status: str | None,
) -> bool:
    return status is None or row.status == status


def sort_operator_rows(
    rows: Sequence[OperatorSessionSummaryView],
    *,
    sort: OperatorSortName,
) -> list[OperatorSessionSummaryView]:
    if sort == OPERATOR_SORT_UPDATED_AT:
        return sorted(
            rows,
            key=lambda row: (
                -row.updated_at.replace(tzinfo=UTC).timestamp(),
                row.priority_rank,
                str(row.session_id),
            ),
        )

    return sorted(
        rows,
        key=lambda row: (
            row.priority_rank,
            -row.updated_at.replace(tzinfo=UTC).timestamp(),
            str(row.session_id),
        ),
    )


def operator_queue_memberships(
    summary: SessionSummaryView,
    *,
    live_actionable: bool,
    historical_only: bool,
    action_needed: bool,
) -> list[str]:
    queue_memberships: list[str] = []
    if summary.pending_approval_id is not None:
        queue_memberships.append(OPERATOR_QUEUE_APPROVALS)
    if summary.pending_question_id is not None:
        queue_memberships.append(OPERATOR_QUEUE_QUESTIONS)
    if summary.status == "failed":
        queue_memberships.append(OPERATOR_QUEUE_FAILURES)
    if summary.projection_health.degraded:
        queue_memberships.append(OPERATOR_QUEUE_DEGRADED)
    if (
        _has_provider_recovery_attention(summary)
        and OPERATOR_QUEUE_DEGRADED not in queue_memberships
    ):
        queue_memberships.append(OPERATOR_QUEUE_DEGRADED)
    if live_actionable:
        queue_memberships.append(OPERATOR_QUEUE_ACTIVE)
    if action_needed:
        queue_memberships.append(OPERATOR_QUEUE_ACTION_NEEDED)
    if historical_only:
        queue_memberships.append(OPERATOR_QUEUE_HISTORICAL)
    return queue_memberships


def _has_recovery_action(summary: SessionSummaryView) -> bool:
    return (
        summary.turn_recovery_posture is not None
        and summary.turn_recovery_posture.state in _RECOVERY_ACTION_STATES
    )


def _has_provider_recovery_attention(summary: SessionSummaryView) -> bool:
    recovery = summary.latest_provider_recovery
    return recovery is not None and (
        recovery.degraded or not recovery.safe_to_continue or recovery.retryable
    )


def queue_count(
    rows: Sequence[OperatorSessionSummaryView],
    queue_name: str,
) -> int:
    return sum(queue_name in row.queue_memberships for row in rows)


def session_queue_counts(
    rows: Sequence[OperatorSessionSummaryView],
) -> SessionQueueCountsView:
    return SessionQueueCountsView(
        total=len(rows),
        approvals=queue_count(rows, OPERATOR_QUEUE_APPROVALS),
        questions=queue_count(rows, OPERATOR_QUEUE_QUESTIONS),
        failures=queue_count(rows, OPERATOR_QUEUE_FAILURES),
        degraded=queue_count(rows, OPERATOR_QUEUE_DEGRADED),
        active=queue_count(rows, OPERATOR_QUEUE_ACTIVE),
        action_needed=queue_count(rows, OPERATOR_QUEUE_ACTION_NEEDED),
        historical=queue_count(rows, OPERATOR_QUEUE_HISTORICAL),
    )


def projection_health_counts(
    rows: Sequence[OperatorSessionSummaryView],
) -> ProjectionHealthCountsView:
    counts = ProjectionHealthCountsView()
    for row in rows:
        state = row.projection_health.state
        if state == "ok":
            counts.ok += 1
        elif state == "stale":
            counts.stale += 1
        elif state == "unavailable":
            counts.unavailable += 1
        if row.projection_health.degraded:
            counts.degraded += 1
    return counts
