"""Read-only query models and service for durable task plans."""

from datetime import datetime
from typing import Any
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import EventId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import TurnId
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.models import TaskVerificationRecord
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import VerificationCheckKind
from glassbox.core.types import VerificationFailureCategory
from glassbox.core.types import VerificationPlanSource


class TaskPlanRepository(Protocol):
    """Repository methods required by the task query service."""

    def list_tasks(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskRecord]: ...

    def get_task(self, task_id: TaskId) -> TaskRecord | None: ...

    def list_task_steps(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskStepRecord]: ...

    def list_task_verifications(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskVerificationRecord]: ...

    def list_task_verification_ledger(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskVerificationLedgerRecord]: ...

    def get_task_verification_ledger_summary(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> TaskVerificationLedgerSummary: ...

    def read_session_events_after(
        self,
        session_id: SessionId,
        after_sequence: int,
        *,
        limit: int | None = None,
    ) -> list[EventEnvelope]: ...


class TaskSummaryView(BaseModel):
    """Operator-facing task summary."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    session_id: SessionId
    title: str
    goal: str
    status: TaskPlanStatus
    updated_at: datetime
    blocked_reason: TaskBlockedReason | None = None
    blocked_detail: str | None = None
    current_step_id: TaskStepId | None = None
    step_count: int = Field(ge=0)
    next_action_summary: str


class TaskStepView(BaseModel):
    """Operator-facing task step detail."""

    model_config = ConfigDict(extra="forbid")

    step_id: TaskStepId
    title: str
    order: int = Field(ge=0)
    status: TaskStepStatus
    description: str | None = None
    blocked_reason: TaskBlockedReason | None = None


class TaskVerificationView(BaseModel):
    """Operator-facing verification detail for a task."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str
    status: TaskVerificationStatus
    step_id: TaskStepId | None = None
    summary: str | None = None


class TaskVerificationLedgerView(BaseModel):
    """Operator-facing long-run verification ledger entry."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str
    status: TaskVerificationStatus
    step_id: TaskStepId | None = None
    kind: VerificationCheckKind | None = None
    source: VerificationPlanSource | None = None
    command: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    eval_case_id: str | None = None
    eval_profile_id: str | None = None
    blocking: bool = True
    attempt_count: int = Field(ge=0)
    latest_attempt: int = Field(ge=0)
    planned_sequence: int | None = Field(default=None, ge=0)
    started_sequence: int | None = Field(default=None, ge=0)
    last_success_sequence: int | None = Field(default=None, ge=0)
    latest_failed_sequence: int | None = Field(default=None, ge=0)
    latest_failed_summary: str | None = None
    latest_failed_category: VerificationFailureCategory | None = None
    latest_failed_artifact_id: str | None = None
    latest_artifact_id: str | None = None
    accepted_risk_count: int = Field(ge=0)
    accepted_risks: list[str] = Field(default_factory=list)
    residual_risk_reason: str | None = None
    summary: str | None = None
    updated_at: datetime
    last_sequence: int = Field(ge=0)


class TaskVerificationLedgerSummaryView(BaseModel):
    """Operator-facing verification posture summary."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    total_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    running_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)
    latest_success_verification_id: TaskVerificationId | None = None
    latest_success_check_name: str | None = None
    latest_success_sequence: int | None = Field(default=None, ge=0)
    latest_failed_verification_id: TaskVerificationId | None = None
    latest_failed_check_name: str | None = None
    latest_failed_sequence: int | None = Field(default=None, ge=0)
    latest_failed_summary: str | None = None
    current_posture: str


class TaskEventView(BaseModel):
    """Task-related event detail for CLI and API reads."""

    model_config = ConfigDict(extra="forbid")

    event_id: EventId
    session_id: SessionId
    sequence: int = Field(ge=0)
    event_type: str
    created_at: datetime
    task_id: TaskId
    turn_id: TurnId | None = None
    payload: dict[str, Any]


class TaskDetailView(BaseModel):
    """Full read-only task detail."""

    model_config = ConfigDict(extra="forbid")

    task: TaskSummaryView
    steps: list[TaskStepView]
    verifications: list[TaskVerificationView]
    verification_ledger: list[TaskVerificationLedgerView]
    verification_summary: TaskVerificationLedgerSummaryView


class TaskQueryService:
    """Read-only task-plan query service."""

    def __init__(self, repository: TaskPlanRepository) -> None:
        self._repository = repository

    def list_task_summaries(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskSummaryView]:
        return [
            _summary_from_record(record)
            for record in self._repository.list_tasks(
                session_id=session_id,
                limit=limit,
                offset=offset,
            )
        ]

    def get_task_detail(self, task_id: TaskId) -> TaskDetailView:
        record = self._repository.get_task(task_id)
        if record is None:
            raise ValueError(f"unknown task_id: {task_id}")
        return TaskDetailView(
            task=_summary_from_record(record),
            steps=[
                _step_view_from_record(step)
                for step in self._repository.list_task_steps(
                    record.session_id,
                    record.task_id,
                )
            ],
            verifications=[
                _verification_view_from_record(verification)
                for verification in self._repository.list_task_verifications(
                    record.session_id,
                    record.task_id,
                )
            ],
            verification_ledger=[
                _verification_ledger_view_from_record(entry)
                for entry in self._repository.list_task_verification_ledger(
                    record.session_id,
                    record.task_id,
                )
            ],
            verification_summary=_verification_summary_view_from_record(
                self._repository.get_task_verification_ledger_summary(
                    record.session_id,
                    record.task_id,
                )
            ),
        )

    def list_task_events(
        self,
        task_id: TaskId,
        *,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[TaskEventView]:
        record = self._repository.get_task(task_id)
        if record is None:
            raise ValueError(f"unknown task_id: {task_id}")
        matched_events: list[TaskEventView] = []
        for event in self._repository.read_session_events_after(
            record.session_id,
            after_sequence,
        ):
            if event.task_id != task_id:
                continue
            matched_events.append(_event_view_from_envelope(event, task_id))
            if limit is not None and len(matched_events) >= limit:
                break
        return matched_events


def _summary_from_record(record: TaskRecord) -> TaskSummaryView:
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
        next_action_summary=_next_action_summary(record),
    )


def _step_view_from_record(record: TaskStepRecord) -> TaskStepView:
    return TaskStepView(
        step_id=record.step_id,
        title=record.title,
        order=record.order,
        status=record.status,
        description=record.description,
        blocked_reason=record.blocked_reason,
    )


def _verification_view_from_record(
    record: TaskVerificationRecord,
) -> TaskVerificationView:
    return TaskVerificationView(
        verification_id=record.verification_id,
        check_name=record.check_name,
        status=record.status,
        step_id=record.step_id,
        summary=record.summary,
    )


def _verification_ledger_view_from_record(
    record: TaskVerificationLedgerRecord,
) -> TaskVerificationLedgerView:
    return TaskVerificationLedgerView(
        verification_id=record.verification_id,
        check_name=record.check_name,
        status=record.status,
        step_id=record.step_id,
        kind=record.kind,
        source=record.source,
        command=record.command,
        changed_paths=[str(path) for path in record.changed_paths],
        eval_case_id=record.eval_case_id,
        eval_profile_id=record.eval_profile_id,
        blocking=record.blocking,
        attempt_count=record.attempt_count,
        latest_attempt=record.latest_attempt,
        planned_sequence=record.planned_sequence,
        started_sequence=record.started_sequence,
        last_success_sequence=record.last_success_sequence,
        latest_failed_sequence=record.latest_failed_sequence,
        latest_failed_summary=record.latest_failed_summary,
        latest_failed_category=record.latest_failed_category,
        latest_failed_artifact_id=(
            str(record.latest_failed_artifact_id)
            if record.latest_failed_artifact_id
            else None
        ),
        latest_artifact_id=(
            str(record.latest_artifact_id) if record.latest_artifact_id else None
        ),
        accepted_risk_count=record.accepted_risk_count,
        accepted_risks=record.accepted_risks,
        residual_risk_reason=record.residual_risk_reason,
        summary=record.summary,
        updated_at=record.updated_at,
        last_sequence=record.last_sequence,
    )


def _verification_summary_view_from_record(
    record: TaskVerificationLedgerSummary,
) -> TaskVerificationLedgerSummaryView:
    return TaskVerificationLedgerSummaryView.model_validate(
        record.model_dump(mode="python")
    )


def _event_view_from_envelope(
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


def _next_action_summary(record: TaskRecord) -> str:
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


__all__ = [
    "TaskDetailView",
    "TaskEventView",
    "TaskPlanRepository",
    "TaskQueryService",
    "TaskStepView",
    "TaskSummaryView",
    "TaskVerificationView",
    "TaskVerificationLedgerSummaryView",
    "TaskVerificationLedgerView",
]
