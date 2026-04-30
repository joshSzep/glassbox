"""HTTP transport models and serializers for the session API."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import ForkedSession
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
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


class ToolCallResponse(ActiveToolCallResponse):
    """Tool-call detail row for paginated session reads."""


class ToolAttemptResponse(BaseModel):
    tool_attempt_id: str
    session_id: str
    turn_id: str
    tool_name: str
    status: str
    tool_call_id: str | None = None
    task_id: str | None = None
    message: str | None = None
    started_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    heartbeat_expires_at: datetime | None = None
    completed_at: datetime | None = None
    completed_units: int | None = None
    total_units: int | None = None
    output_artifact_id: str | None = None
    safe_to_retry: bool | None = None
    retry_classification: str | None = None
    retry_requires_approval: bool | None = None
    retry_reason: str | None = None
    retry_policy_reason: str | None = None
    last_sequence: int


class ToolAttemptArtifactReferenceResponse(BaseModel):
    artifact_id: str
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = None


class ToolAttemptInspectionResponse(BaseModel):
    attempt: ToolAttemptResponse
    source_tool_call_id: str | None = None
    source_arguments: dict[str, object] | None = None
    output_artifact: ToolAttemptArtifactReferenceResponse | None = None
    correlated_event_count: int
    recovery_actions: list[str]


class ToolAttemptRecoveryRequest(BaseModel):
    reason: str | None = None
    actor: str = "operator"
    confirmed: bool = False


class ToolAttemptAbandonRequest(BaseModel):
    reason: str
    actor: str = "operator"
    confirmed: bool = False


class ToolAttemptRecoveryResponse(BaseModel):
    message: str
    original_attempt: ToolAttemptResponse
    retry_attempt: ToolAttemptResponse | None = None


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


class TurnRecoveryPostureResponse(BaseModel):
    turn_id: str
    state: str
    safe_to_resume: bool | None = None
    reason: str | None = None
    next_action: str
    source_event_type: str | None = None
    recovery_decision_id: str | None = None


class LongRunStatusResponse(BaseModel):
    state: str
    current_phase: str | None = None
    last_event_type: str | None = None
    last_event_sequence: int | None = None
    last_event_at: datetime | None = None
    current_attempt_id: str | None = None
    current_attempt_tool_name: str | None = None
    current_attempt_status: str | None = None
    heartbeat_at: datetime | None = None
    heartbeat_expires_at: datetime | None = None
    heartbeat_age_seconds: int | None = None
    elapsed_seconds: int
    stuck_reason: str | None = None
    progress_summary: str


class TaskCheckpointResponse(BaseModel):
    checkpoint_id: str
    session_id: str
    task_id: str | None = None
    turn_id: str | None = None
    tool_attempt_id: str | None = None
    compaction_id: str | None = None
    artifact_id: str | None = None
    objective: str
    current_phase: str | None = None
    completed_step: str | None = None
    next_action: str
    blockers: list[str]
    touched_files: list[str]
    verification_status: str | None = None
    budget_status: str | None = None
    recovery_guidance: str
    source_start_sequence: int
    source_end_sequence: int
    created_at: datetime
    last_sequence: int


class ContextCompactionResponse(BaseModel):
    compaction_id: str
    session_id: str
    scope: str
    source_start_sequence: int
    source_end_sequence: int
    summary: str
    artifact_id: str
    artifact_schema_version: int
    freshness: str
    freshness_reason: str | None = None
    superseded_by_compaction_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    checkpoint_id: str | None = None
    source_artifact_ids: list[str]
    decision_count: int
    unresolved_question_count: int
    accepted_risk_count: int
    limitations: list[str]
    created_at: datetime
    last_sequence: int


class ProjectionHealthResponse(BaseModel):
    state: str
    canonical_last_sequence: int
    projected_last_sequence: int | None
    lag: int
    estimated_rebuild_event_count: int
    projected_progress_ratio: float | None
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


class PageInfoResponse(BaseModel):
    cursor: int
    limit: int
    next_cursor: int | None
    has_more: bool
    returned_count: int


class EventLogEntryResponse(BaseModel):
    event_id: str
    session_id: str
    sequence: int
    event_type: str
    event_version: int
    created_at: datetime
    payload: dict[str, object]


class ArtifactDetailResponse(BaseModel):
    sequence: int
    event_type: str
    artifact_id: str
    artifact_kind: str
    path: str | None = None
    tool_call_id: str | None = None
    turn_id: str
    content_sha256: str | None = None
    size_bytes: int | None = None


class SessionTranscriptPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[TranscriptMessageResponse]


class SessionEventLogPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[EventLogEntryResponse]


class SessionToolCallPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[ToolCallResponse]


class SessionTurnMetricsPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[TurnMetricsResponse]


class SessionCheckpointPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[TaskCheckpointResponse]


class SessionCompactionPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[ContextCompactionResponse]


class RefreshContextCompactionRequest(BaseModel):
    reason: str | None = None
    confirmed: bool = False


class RefreshContextCompactionResponse(BaseModel):
    refreshed_compaction: ContextCompactionResponse
    previous_compaction_id: str
    previous_freshness: str
    previous_freshness_reason: str
    superseded_by_compaction_id: str


class InvalidateContextCompactionRequest(BaseModel):
    reason: str
    confirmed: bool = False


class InvalidateContextCompactionResponse(BaseModel):
    compaction_id: str
    freshness: str
    freshness_reason: str


class SessionArtifactPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[ArtifactDetailResponse]


class SessionSummaryResponse(BaseModel):
    session_id: str
    status: str
    model_name: str
    cwd: str
    approval_mode: str
    budget_posture: AutonomyBudgetPostureRecord | None = None
    approval_behavior: str = ""
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
    turn_recovery_posture: TurnRecoveryPostureResponse | None = None
    latest_checkpoint: TaskCheckpointResponse | None = None
    long_run_status: LongRunStatusResponse
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
    background_job_failed_count: int = 0
    background_job_retryable_count: int = 0
    background_job_abandoned_count: int = 0


class ProviderEvidenceSummaryResponse(BaseModel):
    advisory: bool = True
    summary_count: int = 0
    latest_summary_path: str | None = None
    latest_generated_at: str | None = None
    latest_status: str = "missing"
    freshness_status: str = "missing"
    freshness_policy_version: str = "provider-evidence-freshness.v1"
    stale_after_seconds: int = 604800
    schema_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    configured_model_name: str | None = None
    identity_matches_current_config: bool | None = None
    diagnostics_state: str | None = None
    scenario_count: int = 0
    matrix_entry_count: int = 0
    missing_scenarios: list[str] = Field(default_factory=list)
    passed_count: int = 0
    skipped_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    stale: bool = False
    next_actions: list[str] = Field(default_factory=list)


class SessionAggregateResponse(BaseModel):
    queue: str | None
    status: str | None
    sort: str
    limit: int | None
    queue_counts: SessionQueueCountsResponse
    projection_health_counts: ProjectionHealthCountsAggregateResponse
    runtime: WorkspaceRuntimeSummaryResponse
    provider_evidence: ProviderEvidenceSummaryResponse = Field(
        default_factory=ProviderEvidenceSummaryResponse
    )
    sessions: list[OperatorSessionSummaryResponse]


class SessionSnapshotResponse(BaseModel):
    session_id: str
    status: str
    current_turn_id: str | None
    model_name: str
    cwd: str
    approval_mode: str
    budget_posture: AutonomyBudgetPostureRecord | None = None
    approval_behavior: str = ""
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
    turn_recovery_posture: TurnRecoveryPostureResponse | None = None
    latest_checkpoint: TaskCheckpointResponse | None = None
    checkpoint_history: list[TaskCheckpointResponse]
    long_run_status: LongRunStatusResponse
    active_tool_calls: list[ActiveToolCallResponse]
    recent_tool_attempts: list[ToolAttemptResponse] = Field(default_factory=list)
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


def build_provider_evidence_summary_response(
    evidence: ProviderCanaryEvidenceSummary,
) -> ProviderEvidenceSummaryResponse:
    """Serialize retained provider evidence for dashboard aggregate payloads."""

    return ProviderEvidenceSummaryResponse.model_validate(
        {"advisory": True, **evidence.model_dump(mode="json")}
    )


def build_session_snapshot_response(
    snapshot: SessionSnapshotView,
) -> SessionSnapshotResponse:
    """Serialize a session snapshot view into the HTTP response model."""

    return SessionSnapshotResponse.model_validate(snapshot.model_dump(mode="json"))
