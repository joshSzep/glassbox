"""HTTP transport models and serializers for task-plan APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import AutonomyBudget
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import ProjectionHealth
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import AutonomyMode
from glassbox.core.types import PauseWindowPolicy
from glassbox.core.types import TaskBlockedReason
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskEventView
from glassbox.runtime.task_queries import TaskStepView
from glassbox.runtime.task_queries import TaskSummaryView
from glassbox.runtime.task_queries import TaskVerificationLedgerSummaryView
from glassbox.runtime.task_queries import TaskVerificationLedgerView
from glassbox.runtime.task_queries import TaskVerificationView
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.session_api import ProjectionHealthResponse


class TaskSummaryResponse(BaseModel):
    task_id: str
    session_id: str
    title: str
    goal: str
    status: str
    updated_at: datetime
    blocked_reason: str | None = None
    blocked_detail: str | None = None
    current_step_id: str | None = None
    step_count: int
    next_action_summary: str


class TaskStepResponse(BaseModel):
    step_id: str
    title: str
    order: int
    status: str
    description: str | None = None
    blocked_reason: str | None = None


class TaskVerificationResponse(BaseModel):
    verification_id: str
    check_name: str
    status: str
    step_id: str | None = None
    summary: str | None = None


class TaskVerificationLedgerResponse(BaseModel):
    verification_id: str
    check_name: str
    status: str
    step_id: str | None = None
    kind: str | None = None
    source: str | None = None
    command: list[str]
    changed_paths: list[str]
    eval_case_id: str | None = None
    eval_profile_id: str | None = None
    blocking: bool
    attempt_count: int
    latest_attempt: int
    planned_sequence: int | None = None
    started_sequence: int | None = None
    last_success_sequence: int | None = None
    latest_failed_sequence: int | None = None
    latest_failed_summary: str | None = None
    latest_failed_category: str | None = None
    latest_failed_artifact_id: str | None = None
    latest_artifact_id: str | None = None
    accepted_risk_count: int
    accepted_risks: list[str]
    residual_risk_reason: str | None = None
    summary: str | None = None
    updated_at: datetime
    last_sequence: int


class TaskVerificationLedgerSummaryResponse(BaseModel):
    task_id: str
    total_count: int
    passed_count: int
    failed_count: int
    running_count: int
    skipped_count: int
    accepted_risk_count: int
    latest_success_verification_id: str | None = None
    latest_success_check_name: str | None = None
    latest_success_sequence: int | None = None
    latest_failed_verification_id: str | None = None
    latest_failed_check_name: str | None = None
    latest_failed_sequence: int | None = None
    latest_failed_summary: str | None = None
    current_posture: str


class TaskVerificationDriftResponse(BaseModel):
    task_id: str
    posture: str
    workspace_clean: bool
    changed_paths: list[str]
    material_changed_paths: list[str]
    docs_only_changed_paths: list[str]
    generated_changed_paths: list[str]
    stale_verification_ids: list[str]
    stale_changed_paths: list[str]
    changed_path_digest: str | None = None
    diff_summary_command: str | None = None
    reason: str
    error: str | None = None


class TaskEventResponse(BaseModel):
    event_id: str
    session_id: str
    sequence: int
    event_type: str
    created_at: datetime
    task_id: str
    turn_id: str | None = None
    payload: dict[str, object]


class TaskListPageResponse(BaseModel):
    session_id: str | None
    page: PageInfoResponse
    projection_health: ProjectionHealthResponse | None = None
    items: list[TaskSummaryResponse]


class TaskDetailResponse(BaseModel):
    task: TaskSummaryResponse
    steps: list[TaskStepResponse]
    verifications: list[TaskVerificationResponse]
    verification_ledger: list[TaskVerificationLedgerResponse]
    verification_summary: TaskVerificationLedgerSummaryResponse
    verification_drift: TaskVerificationDriftResponse
    projection_health: ProjectionHealthResponse


class TaskStepPageResponse(BaseModel):
    task_id: str
    page: PageInfoResponse
    projection_health: ProjectionHealthResponse
    items: list[TaskStepResponse]


class TaskEventPageResponse(BaseModel):
    task_id: str
    page: PageInfoResponse
    projection_health: ProjectionHealthResponse
    items: list[TaskEventResponse]


class TaskActionRequest(BaseModel):
    actor: str = "operator"
    reason: str | None = None


class TaskPauseRequest(TaskActionRequest):
    detail: str | None = None
    reason: TaskBlockedReason = TaskBlockedReason.MANUAL_PAUSE


class TaskPauseWindowRequest(TaskActionRequest):
    policy: PauseWindowPolicy
    pause_before: datetime | None = None
    checkpoint_id: str | None = None


class TaskPauseWindowCancelRequest(TaskActionRequest):
    reason: str = "operator override"


class TaskPauseWindowResponse(BaseModel):
    pause_window_id: str
    policy: str | None = None
    reason: str
    pause_before: datetime | None = None
    checkpoint_id: str | None = None
    status: str = "scheduled"


class TaskContinueRequest(TaskActionRequest):
    requested_by: str = "operator"
    verify_repair: bool = True
    continue_for_minutes: int | None = Field(default=None, ge=1, le=1440)
    checkpoint_id: str | None = None


class TaskContinuationWindowRequest(TaskActionRequest):
    decision: ApprovalDecision = ApprovalDecision.APPROVED
    requested_by: str = "operator"
    decided_by: str = "operator"
    requested_minutes: int = Field(ge=1, le=1440)
    checkpoint_id: str | None = None
    verify_repair: bool = True


class ContinuationWindowResponse(BaseModel):
    approval_id: str
    decision: str
    requested_minutes: int
    approved_until: datetime | None = None
    checkpoint_id: str | None = None


class TaskBudgetAdjustmentRequest(TaskActionRequest):
    mode: AutonomyMode
    budget: AutonomyBudget
    detail: str | None = None


class BackgroundJobResponse(BaseModel):
    job_id: str
    session_id: str
    state: str
    kind: str
    job_type: str
    title: str
    requested_by: str
    task_id: str | None = None
    progress_message: str | None = None
    failure_kind: str | None = None
    failure_message: str | None = None
    retryable: bool = False


class TaskContinuationWindowActionResponse(BaseModel):
    status: str
    continuation_window: ContinuationWindowResponse
    job: BackgroundJobResponse | None = None


class BackgroundJobDetailResponse(BaseModel):
    job: BackgroundJobResponse


def build_task_summary_response(summary: TaskSummaryView) -> TaskSummaryResponse:
    """Serialize a task summary view into the HTTP response model."""

    return TaskSummaryResponse.model_validate(summary.model_dump(mode="json"))


def build_task_summary_responses(
    summaries: Sequence[TaskSummaryView],
) -> list[TaskSummaryResponse]:
    """Serialize multiple task summary views."""

    return [build_task_summary_response(summary) for summary in summaries]


def build_task_step_response(step: TaskStepView) -> TaskStepResponse:
    """Serialize a task step view into the HTTP response model."""

    return TaskStepResponse.model_validate(step.model_dump(mode="json"))


def build_task_step_responses(
    steps: Sequence[TaskStepView],
) -> list[TaskStepResponse]:
    """Serialize multiple task step views."""

    return [build_task_step_response(step) for step in steps]


def build_task_verification_response(
    verification: TaskVerificationView,
) -> TaskVerificationResponse:
    """Serialize a task verification view into the HTTP response model."""

    return TaskVerificationResponse.model_validate(verification.model_dump(mode="json"))


def build_task_verification_ledger_response(
    entry: TaskVerificationLedgerView,
) -> TaskVerificationLedgerResponse:
    """Serialize one verification-ledger entry into an HTTP response model."""

    return TaskVerificationLedgerResponse.model_validate(entry.model_dump(mode="json"))


def build_task_verification_summary_response(
    summary: TaskVerificationLedgerSummaryView,
) -> TaskVerificationLedgerSummaryResponse:
    """Serialize verification posture into an HTTP response model."""

    return TaskVerificationLedgerSummaryResponse.model_validate(
        summary.model_dump(mode="json")
    )


def build_task_event_response(event: TaskEventView) -> TaskEventResponse:
    """Serialize a task event view into the HTTP response model."""

    return TaskEventResponse.model_validate(event.model_dump(mode="json"))


def build_task_event_responses(
    events: Sequence[TaskEventView],
) -> list[TaskEventResponse]:
    """Serialize multiple task event views."""

    return [build_task_event_response(event) for event in events]


def build_task_detail_response(
    detail: TaskDetailView,
    projection_health: ProjectionHealth,
) -> TaskDetailResponse:
    """Serialize a task detail view with projection-health context."""

    return TaskDetailResponse(
        task=build_task_summary_response(detail.task),
        steps=build_task_step_responses(detail.steps),
        verifications=[
            build_task_verification_response(verification)
            for verification in detail.verifications
        ],
        verification_ledger=[
            build_task_verification_ledger_response(entry)
            for entry in detail.verification_ledger
        ],
        verification_summary=build_task_verification_summary_response(
            detail.verification_summary
        ),
        verification_drift=TaskVerificationDriftResponse.model_validate(
            detail.verification_drift.model_dump(mode="json")
        ),
        projection_health=ProjectionHealthResponse.model_validate(
            projection_health.model_dump(mode="json")
        ),
    )


def build_projection_health_response(
    projection_health: ProjectionHealth,
) -> ProjectionHealthResponse:
    """Serialize projection health for task pages."""

    return ProjectionHealthResponse.model_validate(
        projection_health.model_dump(mode="json")
    )


def build_background_job_response(job: BackgroundJobRecord) -> BackgroundJobResponse:
    """Serialize a background job record into dashboard action output."""

    payload = job.model_dump(mode="json")
    return BackgroundJobResponse.model_validate(payload)
