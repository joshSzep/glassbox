"""Selected-session snapshot and summary response models."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.web.session_api_common import ActiveToolCallResponse
from glassbox.web.session_api_common import LongRunStatusResponse
from glassbox.web.session_api_common import PendingApprovalResponse
from glassbox.web.session_api_common import PolicyActivitySummaryResponse
from glassbox.web.session_api_common import ProjectionHealthResponse
from glassbox.web.session_api_common import ProviderRecoveryResponse
from glassbox.web.session_api_common import TaskCheckpointResponse
from glassbox.web.session_api_common import ToolAttemptResponse
from glassbox.web.session_api_common import TranscriptMessageResponse
from glassbox.web.session_api_common import TurnMetricsResponse
from glassbox.web.session_api_common import TurnRecoveryPostureResponse


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
    latest_provider_recovery: ProviderRecoveryResponse | None = None
    long_run_status: LongRunStatusResponse
    latest_message_summary: str | None
    projection_health: ProjectionHealthResponse
    next_action_summary: str


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
    latest_provider_recovery: ProviderRecoveryResponse | None = None
    long_run_status: LongRunStatusResponse
    active_tool_calls: list[ActiveToolCallResponse]
    recent_tool_attempts: list[ToolAttemptResponse] = Field(default_factory=list)
    pending_approvals: list[PendingApprovalResponse]
    session_policy_summary: PolicyActivitySummaryResponse
    current_turn_policy_summary: PolicyActivitySummaryResponse | None
    turn_metrics: list[TurnMetricsResponse]
    runtime_context: RuntimeContextSnapshot
    projection_health: ProjectionHealthResponse
