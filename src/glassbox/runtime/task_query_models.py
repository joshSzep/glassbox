"""Transport-agnostic task query models shared by CLI and web consumers."""

from datetime import datetime
from typing import Any
from typing import Literal
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import EventId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import TurnId
from glassbox.core.models import TaskCheckpointRecord
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
from glassbox.runtime.verification_drift import VerificationDriftAssessment


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

    def list_task_checkpoints(
        self,
        session_id: SessionId,
        *,
        task_id: TaskId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskCheckpointRecord]: ...

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


class TaskLastKnownGoodView(BaseModel):
    """Operator-facing marker for the latest successful verification point."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    verification_id: TaskVerificationId
    check_name: str
    sequence: int = Field(ge=0)
    summary: str | None = None
    artifact_id: str | None = None
    checkpoint_id: TaskCheckpointId | None = None
    checkpoint_sequence: int | None = Field(default=None, ge=0)
    checkpoint_objective: str | None = None
    changed_paths: list[str] = Field(default_factory=list)
    changed_path_digest: str | None = None
    drift_posture: str
    evidence_status: Literal["fresh", "stale", "unknown"]
    stale_paths: list[str] = Field(default_factory=list)


class TaskRepairAttemptView(BaseModel):
    """One retry edge in the task verification repair history."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    next_verification_id: TaskVerificationId
    attempt: int = Field(ge=1)
    reason: str
    source_sequence: int = Field(ge=0)
    failed_summary: str | None = None
    failed_artifact_id: str | None = None
    repaired: bool = False
    accepted_risk_count: int = Field(default=0, ge=0)


class TaskRepairHistoryView(BaseModel):
    """Current task-local verify-repair posture and compact retry history."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    status: Literal[
        "no_verification",
        "clean",
        "partial",
        "failed",
        "repairing",
        "repaired",
        "accepted_with_risk",
        "regressed",
    ]
    failure_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    repaired_count: int = Field(ge=0)
    repeated_failure_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)
    latest_failure_sequence: int | None = Field(default=None, ge=0)
    latest_failure_summary: str | None = None
    attempts: list[TaskRepairAttemptView] = Field(default_factory=list)


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
    verification_drift: VerificationDriftAssessment
    last_known_good: TaskLastKnownGoodView | None = None
    repair_history: TaskRepairHistoryView


__all__ = [
    "TaskDetailView",
    "TaskEventView",
    "TaskLastKnownGoodView",
    "TaskPlanRepository",
    "TaskRepairAttemptView",
    "TaskRepairHistoryView",
    "TaskStepView",
    "TaskSummaryView",
    "TaskVerificationLedgerSummaryView",
    "TaskVerificationLedgerView",
    "TaskVerificationView",
]
