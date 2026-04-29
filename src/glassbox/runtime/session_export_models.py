"""Portable session export payload models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import MessageRole
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TurnMetricsRecord
from glassbox.runtime.session_queries import BranchableTurnView
from glassbox.runtime.session_queries import ChildSessionSummaryView

SESSION_EXPORT_KIND = "glassbox_session_export"
SESSION_EXPORT_VERSION = 1


class SessionExportWorkspace(BaseModel):
    """Redacted workspace metadata for a portable session export."""

    model_config = ConfigDict(extra="forbid")

    label: str
    cwd: Literal["<workspace-root>"] = "<workspace-root>"


class SessionExportMetadata(BaseModel):
    """Core session metadata that is useful during handoff."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: str
    model_name: str
    approval_mode: str
    created_at: datetime
    updated_at: datetime
    last_sequence: int = Field(ge=0)
    workspace: SessionExportWorkspace


class SessionExportLineage(BaseModel):
    """Lineage and forkability metadata for a session export."""

    model_config = ConfigDict(extra="forbid")

    parent_session_id: SessionId | None = None
    forked_from_turn_id: str | None = None
    forked_from_sequence: int | None = Field(default=None, ge=0)
    branch_label: str | None = None
    child_sessions: list[ChildSessionSummaryView] = Field(default_factory=list)
    branchable_turns: list[BranchableTurnView] = Field(default_factory=list)
    can_fork: bool
    latest_fork_point_turn_id: str | None = None
    latest_fork_point_sequence: int | None = None
    fork_blocked_reason: str | None = None


class SessionExportHandoff(BaseModel):
    """Operator-facing handoff context for the exported session."""

    model_config = ConfigDict(extra="forbid")
    exported_by: str | None = None
    expected_custodian: str | None = None
    note: str | None = None
    last_actor_hint: str | None = None
    next_action_summary: str
    pending_approval_id: str | None = None
    pending_question_id: str | None = None
    pending_question_text: str | None = None
    session_failure_message: str | None = None
    session_failure_retryable: bool | None = None
    historical_only: bool
    live_actionable: bool


class SessionExportTranscriptMessage(BaseModel):
    """Portable transcript message with redacted text parts."""

    model_config = ConfigDict(extra="forbid")
    message_id: str
    role: MessageRole
    parts: list[MessagePart] = Field(default_factory=list)
    created_at: datetime


class SessionExportArtifactReference(BaseModel):
    """Reference to retained evidence without embedding artifact contents."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    event_type: str
    turn_id: str | None = None
    tool_call_id: str | None = None
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class SessionExportEventSummary(BaseModel):
    """Minimal event-log summary suitable for portable review."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    event_type: str
    created_at: datetime
    turn_id: str | None = None
    message_id: str | None = None
    tool_call_id: str | None = None
    approval_id: str | None = None


class SessionExportTaskSummary(BaseModel):
    """Portable task-plan summary for handoff inspection."""

    model_config = ConfigDict(extra="forbid")
    task_id: TaskId
    title: str
    goal: str
    status: str
    updated_at: datetime
    blocked_reason: str | None = None
    blocked_detail: str | None = None
    current_step_id: TaskStepId | None = None
    step_count: int = Field(ge=0)
    next_action_summary: str


class SessionExportTaskStepSummary(BaseModel):
    """Portable task-step summary for handoff inspection."""

    model_config = ConfigDict(extra="forbid")
    task_id: TaskId
    step_id: TaskStepId
    title: str
    order: int = Field(ge=0)
    status: str
    description: str | None = None
    blocked_reason: str | None = None


class SessionExportTaskVerificationSummary(BaseModel):
    """Portable task verification summary for handoff inspection."""

    model_config = ConfigDict(extra="forbid")
    task_id: TaskId
    verification_id: TaskVerificationId
    check_name: str
    status: str
    step_id: TaskStepId | None = None
    summary: str | None = None


class SessionExportTaskEventReference(BaseModel):
    """Canonical task event reference retained for task-aware import/replay."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    event_type: str
    created_at: datetime
    task_id: TaskId
    turn_id: str | None = None
    payload: dict[str, object]


class SessionExportPolicyDecision(BaseModel):
    """Portable policy evidence captured from canonical events."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    event_type: str
    turn_id: str | None = None
    tool_call_id: str | None = None
    approval_id: str | None = None
    tool_name: str | None = None
    subject: str | None = None
    trace: PolicyDecisionTrace


class SessionExportPayload(BaseModel):
    """Inspectable portable session export package."""

    model_config = ConfigDict(extra="forbid")
    export_kind: Literal["glassbox_session_export"] = SESSION_EXPORT_KIND
    export_version: int = SESSION_EXPORT_VERSION
    exported_at: datetime
    metadata: SessionExportMetadata
    lineage: SessionExportLineage
    handoff: SessionExportHandoff
    autonomy_budget_posture: AutonomyBudgetPostureRecord | None = None
    transcript: list[SessionExportTranscriptMessage] = Field(default_factory=list)
    active_tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pending_approvals: list[ApprovalRecord] = Field(default_factory=list)
    turn_metrics: list[TurnMetricsRecord] = Field(default_factory=list)
    artifact_references: list[SessionExportArtifactReference] = Field(
        default_factory=list
    )
    policy_decisions: list[SessionExportPolicyDecision] = Field(default_factory=list)
    task_summaries: list[SessionExportTaskSummary] = Field(default_factory=list)
    task_step_summaries: list[SessionExportTaskStepSummary] = Field(
        default_factory=list
    )
    task_verification_summaries: list[SessionExportTaskVerificationSummary] = Field(
        default_factory=list
    )
    task_event_references: list[SessionExportTaskEventReference] = Field(
        default_factory=list
    )
    event_count: int = Field(ge=0)
    events: list[SessionExportEventSummary] = Field(default_factory=list)
    redaction_notes: list[str] = Field(default_factory=list)
