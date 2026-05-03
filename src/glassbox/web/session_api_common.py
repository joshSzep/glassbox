"""Shared detail-page and diagnostic response models for the session API."""

from datetime import datetime

from pydantic import BaseModel


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
    command_purpose: str | None = None
    command_review_relevance: str | None = None
    command_supports_verification: bool | None = None
    command_purpose_reason: str | None = None
    last_sequence: int


class ToolAttemptArtifactReferenceResponse(BaseModel):
    artifact_id: str
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = None


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


class CheckpointAbsenceResponse(BaseModel):
    reason: str
    severity: str
    message: str
    next_action: str


class ProviderRecoveryResponse(BaseModel):
    session_id: str
    provider: str
    model_name: str
    failure_kind: str
    action: str
    reason: str
    retryable: bool
    safe_to_continue: bool
    degraded: bool = False
    operator_next_action: str
    turn_id: str | None = None
    task_id: str | None = None
    checkpoint_id: str | None = None
    attempt: int
    max_attempts: int | None = None
    backoff_seconds: int | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    last_sequence: int


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


class SessionArtifactPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[ArtifactDetailResponse]
