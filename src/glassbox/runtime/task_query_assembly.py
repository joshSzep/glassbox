"""Record-to-view assembly helpers for task queries."""

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationRecord
from glassbox.core.types import TaskPlanStatus
from glassbox.runtime.task_query_models import TaskEventView
from glassbox.runtime.task_query_models import TaskStepView
from glassbox.runtime.task_query_models import TaskSummaryView
from glassbox.runtime.task_query_models import TaskVerificationView


def summary_from_record(record: TaskRecord) -> TaskSummaryView:
    return TaskSummaryView(
        task_id=record.task_id,
        session_id=record.session_id,
        title=record.title,
        goal=record.goal,
        status=record.status,
        updated_at=record.updated_at,
        blocked_reason=record.blocked_reason,
        blocked_detail=record.blocked_detail,
        current_step_id=record.current_step_id,
        step_count=record.step_count,
        next_action_summary=next_action_summary(record),
    )


def step_view_from_record(record: TaskStepRecord) -> TaskStepView:
    return TaskStepView(
        step_id=record.step_id,
        title=record.title,
        order=record.order,
        status=record.status,
        description=record.description,
        blocked_reason=record.blocked_reason,
    )


def verification_view_from_record(
    record: TaskVerificationRecord,
) -> TaskVerificationView:
    return TaskVerificationView(
        verification_id=record.verification_id,
        check_name=record.check_name,
        status=record.status,
        step_id=record.step_id,
        summary=record.summary,
    )


def event_view_from_envelope(
    event: EventEnvelope,
    task_id: TaskId,
) -> TaskEventView:
    return TaskEventView(
        event_id=event.event_id,
        session_id=event.session_id,
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        task_id=task_id,
        turn_id=event.turn_id,
        payload=event.payload.model_dump(mode="json"),
    )


def next_action_summary(record: TaskRecord) -> str:
    if record.blocked_reason is not None:
        return f"blocked: {record.blocked_reason.value}"
    if record.status == TaskPlanStatus.PROPOSED:
        return "review proposed plan"
    if record.status == TaskPlanStatus.ACTIVE:
        return "continue from current step"
    if record.status == TaskPlanStatus.PAUSED:
        return "resume or cancel task"
    if record.status in {
        TaskPlanStatus.COMPLETED,
        TaskPlanStatus.CANCELLED,
        TaskPlanStatus.ABANDONED,
    }:
        return "historical task"
    if record.status == TaskPlanStatus.FAILED:
        return "inspect failure evidence"
    return "inspect task"
