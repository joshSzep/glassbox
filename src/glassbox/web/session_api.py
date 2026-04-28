"""HTTP transport models and serializers for the session API."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from glassbox.core.models import ForkedSession
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.runtime.session_queries import SessionAggregateView
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.session_queries import SessionSummaryView


class MessagePartResponse(BaseModel):
    kind: str
    text: str


class TranscriptMessageResponse(BaseModel):
    message_id: str
    role: str
    parts: list[MessagePartResponse]
    created_at: datetime


class ActiveToolCallResponse(BaseModel):
    tool_call_id: str
    turn_id: str
    tool_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None = None
    summary: str | None = None
    policy_outcome: str | None = None
    policy_risk_level: str | None = None
    policy_source_kind: str | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None


class PendingApprovalResponse(BaseModel):
    approval_id: str
    turn_id: str
    subject: str
    reason: str
    requested_at: datetime
    policy_outcome: str | None = None
    policy_risk_level: str | None = None
    policy_source_kind: str | None = None
    policy_source_label: str | None = None


class PolicyActivitySummaryResponse(BaseModel):
    total_decisions: int
    allow_count: int
    approve_count: int
    deny_count: int
    blocked_count: int
    read_only_count: int
    workspace_write_count: int
    command_count: int
    highest_risk_level: str | None = None


class TurnMetricsResponse(BaseModel):
    turn_id: str
    started_at: datetime | None
    completed_at: datetime | None
    turn_duration_ms: int | None
    model_call_count: int
    model_duration_ms_total: int
    model_input_tokens_total: int
    model_output_tokens_total: int
    tool_call_count: int
    tool_duration_ms_total: int
    succeeded_tool_call_count: int
    failed_tool_call_count: int


class ProjectionHealthResponse(BaseModel):
    state: str
    canonical_last_sequence: int
    projected_last_sequence: int | None
    lag: int
    degraded: bool
    detail: str | None


class ChildSessionSummaryResponse(BaseModel):
    session_id: str
    status: str
    branch_label: str | None
    updated_at: datetime
    latest_message_summary: str | None


class BranchableTurnResponse(BaseModel):
    turn_id: str
    sequence: int
    created_at: datetime
    label: str


class ForkSessionRequest(BaseModel):
    turn_id: UUID | None = None
    branch_label: str | None = None


class ForkSessionResponse(BaseModel):
    child_session_id: str
    parent_session_id: str
    forked_from_turn_id: str
    forked_from_sequence: int
    branch_label: str | None
    inherited_message_count: int
    last_sequence: int


class SubmitSessionMessageRequest(BaseModel):
    text: str


class SubmitSessionAnswerRequest(BaseModel):
    answer: str


class CancelSessionTurnRequest(BaseModel):
    turn_id: UUID | None = None
    reason: str | None = None


class ActionAcceptedResponse(BaseModel):
    status: str


class ErrorDetailResponse(BaseModel):
    detail: str


class SessionSummaryResponse(BaseModel):
    session_id: str
    status: str
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: str | None
    forked_from_turn_id: str | None
    forked_from_sequence: int | None
    branch_label: str | None
    child_session_count: int
    can_fork: bool
    latest_fork_point_turn_id: str | None
    latest_fork_point_sequence: int | None
    fork_blocked_reason: str | None
    dashboard_url: str | None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None
    pending_question_id: str | None
    pending_question_text: str | None
    session_failure_message: str | None
    session_failure_retryable: bool | None
    latest_message_summary: str | None
    projection_health: ProjectionHealthResponse
    next_action_summary: str


class OperatorSessionSummaryResponse(SessionSummaryResponse):
    queue_memberships: list[str]
    priority_bucket: str
    priority_rank: int
    action_needed: bool
    live_actionable: bool
    historical_only: bool
    has_active_turn: bool


class SessionQueueCountsResponse(BaseModel):
    total: int
    approvals: int
    questions: int
    failures: int
    degraded: int
    active: int
    action_needed: int
    historical: int


class ProjectionHealthCountsAggregateResponse(BaseModel):
    ok: int
    stale: int
    unavailable: int
    degraded: int


class WorkspaceRuntimeSummaryResponse(BaseModel):
    workspace_root: str
    state: str
    health: str | None
    pid: int | None
    dashboard_url: str | None
    health_url: str | None
    session_index_url: str | None
    started_at: datetime | None


class SessionAggregateResponse(BaseModel):
    queue: str | None
    status: str | None
    sort: str
    limit: int | None
    queue_counts: SessionQueueCountsResponse
    projection_health_counts: ProjectionHealthCountsAggregateResponse
    runtime: WorkspaceRuntimeSummaryResponse
    sessions: list[OperatorSessionSummaryResponse]


class SessionSnapshotResponse(BaseModel):
    session_id: str
    status: str
    current_turn_id: str | None
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: str | None
    forked_from_turn_id: str | None
    forked_from_sequence: int | None
    branch_label: str | None
    child_sessions: list[ChildSessionSummaryResponse]
    branchable_turns: list[BranchableTurnResponse]
    can_fork: bool
    latest_fork_point_turn_id: str | None
    latest_fork_point_sequence: int | None
    fork_blocked_reason: str | None
    dashboard_url: str | None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None
    pending_question_id: str | None
    pending_question_text: str | None
    session_failure_message: str | None
    session_failure_retryable: bool | None
    transcript: list[TranscriptMessageResponse]
    active_tool_calls: list[ActiveToolCallResponse]
    pending_approvals: list[PendingApprovalResponse]
    session_policy_summary: PolicyActivitySummaryResponse
    current_turn_policy_summary: PolicyActivitySummaryResponse | None
    turn_metrics: list[TurnMetricsResponse]
    runtime_context: RuntimeContextSnapshot
    projection_health: ProjectionHealthResponse


def build_fork_session_response(forked_session: ForkedSession) -> ForkSessionResponse:
    """Serialize a newly forked session into the HTTP response model."""

    return ForkSessionResponse.model_validate(forked_session.model_dump(mode="json"))


def build_session_summary_response(
    summary: SessionSummaryView,
) -> SessionSummaryResponse:
    """Serialize a session summary view into the HTTP response model."""

    return SessionSummaryResponse.model_validate(summary.model_dump(mode="json"))


def build_session_summary_responses(
    summaries: Sequence[SessionSummaryView],
) -> list[SessionSummaryResponse]:
    """Serialize multiple session summary views for the session index."""

    return [build_session_summary_response(summary) for summary in summaries]


def build_operator_session_summary_response(
    summary: SessionSummaryView,
) -> OperatorSessionSummaryResponse:
    """Serialize an operator-console session summary into the HTTP model."""

    return OperatorSessionSummaryResponse.model_validate(
        summary.model_dump(mode="json")
    )


def build_session_aggregate_response(
    aggregate: SessionAggregateView,
) -> SessionAggregateResponse:
    """Serialize the operator-console aggregate response into HTTP payloads."""

    return SessionAggregateResponse.model_validate(aggregate.model_dump(mode="json"))


def build_session_snapshot_response(
    snapshot: SessionSnapshotView,
) -> SessionSnapshotResponse:
    """Serialize a session snapshot view into the HTTP response model."""

    return SessionSnapshotResponse.model_validate(snapshot.model_dump(mode="json"))
