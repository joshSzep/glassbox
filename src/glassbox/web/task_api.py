"""HTTP transport models and serializers for task-plan APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from glassbox.core.models import ProjectionHealth
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskEventView
from glassbox.runtime.task_queries import TaskStepView
from glassbox.runtime.task_queries import TaskSummaryView
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
