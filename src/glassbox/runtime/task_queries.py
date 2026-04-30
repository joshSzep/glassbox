"""Compatibility facade and read-only service for durable task-plan queries."""

from pathlib import Path

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.runtime.task_query_assembly import event_view_from_envelope
from glassbox.runtime.task_query_assembly import step_view_from_record
from glassbox.runtime.task_query_assembly import summary_from_record
from glassbox.runtime.task_query_assembly import verification_view_from_record
from glassbox.runtime.task_query_models import TaskDetailView
from glassbox.runtime.task_query_models import TaskEventView
from glassbox.runtime.task_query_models import TaskLastKnownGoodView
from glassbox.runtime.task_query_models import TaskPlanRepository
from glassbox.runtime.task_query_models import TaskRepairAttemptView
from glassbox.runtime.task_query_models import TaskRepairHistoryView
from glassbox.runtime.task_query_models import TaskStepView
from glassbox.runtime.task_query_models import TaskSummaryView
from glassbox.runtime.task_query_models import TaskVerificationLedgerSummaryView
from glassbox.runtime.task_query_models import TaskVerificationLedgerView
from glassbox.runtime.task_query_models import TaskVerificationView
from glassbox.runtime.task_query_repair import repair_history_view
from glassbox.runtime.task_query_verification import last_known_good_view
from glassbox.runtime.task_query_verification import (
    verification_ledger_view_from_record,
)
from glassbox.runtime.task_query_verification import (
    verification_summary_view_from_record,
)
from glassbox.runtime.verification_drift import assess_verification_drift
from glassbox.runtime.verification_drift import not_assessed_verification_drift


class TaskQueryService:
    """Read-only task-plan query service."""

    def __init__(
        self,
        repository: TaskPlanRepository,
        *,
        workspace_root: Path | None = None,
    ) -> None:
        self._repository = repository
        self._workspace_root = workspace_root

    def list_task_summaries(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskSummaryView]:
        return [
            summary_from_record(record)
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
        ledger_records = self._repository.list_task_verification_ledger(
            record.session_id,
            record.task_id,
        )
        verification_summary = self._repository.get_task_verification_ledger_summary(
            record.session_id,
            record.task_id,
        )
        verification_drift = (
            assess_verification_drift(
                self._workspace_root,
                task_id=record.task_id,
                ledger=ledger_records,
            )
            if self._workspace_root is not None
            else not_assessed_verification_drift(record.task_id)
        )
        checkpoints = self._repository.list_task_checkpoints(
            record.session_id,
            task_id=record.task_id,
        )
        task_events = [
            event
            for event in self._repository.read_session_events_after(
                record.session_id,
                0,
            )
            if event.task_id == record.task_id
        ]
        return TaskDetailView(
            task=summary_from_record(record),
            steps=[
                step_view_from_record(step)
                for step in self._repository.list_task_steps(
                    record.session_id,
                    record.task_id,
                )
            ],
            verifications=[
                verification_view_from_record(verification)
                for verification in self._repository.list_task_verifications(
                    record.session_id,
                    record.task_id,
                )
            ],
            verification_ledger=[
                verification_ledger_view_from_record(entry) for entry in ledger_records
            ],
            verification_summary=verification_summary_view_from_record(
                verification_summary
            ),
            verification_drift=verification_drift,
            last_known_good=last_known_good_view(
                task_id=record.task_id,
                ledger=ledger_records,
                checkpoints=checkpoints,
                drift=verification_drift,
            ),
            repair_history=repair_history_view(
                task_id=record.task_id,
                ledger=ledger_records,
                events=task_events,
                summary=verification_summary,
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
            matched_events.append(event_view_from_envelope(event, task_id))
            if limit is not None and len(matched_events) >= limit:
                break
        return matched_events


__all__ = [
    "TaskDetailView",
    "TaskEventView",
    "TaskLastKnownGoodView",
    "TaskPlanRepository",
    "TaskRepairAttemptView",
    "TaskRepairHistoryView",
    "TaskQueryService",
    "TaskStepView",
    "TaskSummaryView",
    "TaskVerificationLedgerSummaryView",
    "TaskVerificationLedgerView",
    "TaskVerificationView",
]
