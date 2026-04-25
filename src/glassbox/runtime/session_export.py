"""Portable session export for review and handoff workflows."""

import json
import re
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.ids import SessionId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import MessageRole
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.runtime.session_queries import BranchableTurnView
from glassbox.runtime.session_queries import ChildSessionSummaryView
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

SESSION_EXPORT_KIND = "glassbox_session_export"
SESSION_EXPORT_VERSION = 1

_REDACTION_PLACEHOLDER = "<redacted>"
_WORKSPACE_PLACEHOLDER = "<workspace-root>"
_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b((?:openai|anthropic|api|access|secret|token|password)"
        r"[_-]?(?:api[_-]?)?(?:key|token|secret|password)?)\s*=\s*([^\s,;]+)"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)
_REDACTION_NOTES = [
    "absolute workspace paths are replaced with <workspace-root>",
    "common secret-like tokens and key assignments are replaced with <redacted>",
    "artifact contents are not embedded; only retained artifact references are listed",
]


class SessionExportWorkspace(BaseModel):
    """Redacted workspace metadata for a portable session export."""

    model_config = ConfigDict(extra="forbid")

    label: str
    cwd: Literal["<workspace-root>"] = _WORKSPACE_PLACEHOLDER


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


class SessionExportPayload(BaseModel):
    """Inspectable portable session export package."""

    model_config = ConfigDict(extra="forbid")
    export_kind: Literal["glassbox_session_export"] = SESSION_EXPORT_KIND
    export_version: int = SESSION_EXPORT_VERSION
    exported_at: datetime
    metadata: SessionExportMetadata
    lineage: SessionExportLineage
    handoff: SessionExportHandoff
    transcript: list[SessionExportTranscriptMessage] = Field(default_factory=list)
    active_tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pending_approvals: list[ApprovalRecord] = Field(default_factory=list)
    turn_metrics: list[TurnMetricsRecord] = Field(default_factory=list)
    artifact_references: list[SessionExportArtifactReference] = Field(
        default_factory=list
    )
    event_count: int = Field(ge=0)
    events: list[SessionExportEventSummary] = Field(default_factory=list)
    redaction_notes: list[str] = Field(default_factory=list)


def export_session_package(
    session_id: SessionId,
    output_path: Path,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
) -> Path:
    """Write a portable session export package and return its resolved path."""

    package = build_session_export_payload(
        session_id,
        session_repository=session_repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
        exported_by=exported_by,
        expected_custodian=expected_custodian,
        note=note,
    )
    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    serialized_package = json.dumps(
        package.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )
    resolved_output.write_text(f"{serialized_package}\n", encoding="utf-8")
    return resolved_output


def build_session_export_payload(
    session_id: SessionId,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
) -> SessionExportPayload:
    """Build a portable handoff payload from persisted session state."""

    query_service = SessionQueryService(session_repository, artifact_repository)
    snapshot = query_service.get_session_snapshot(session_id, turn_metrics_limit=25)
    events = session_repository.read_session_events(session_id)
    redaction_context = _RedactionContext(workspace_root=workspace_root.resolve())

    return SessionExportPayload(
        exported_at=datetime.now(UTC),
        metadata=_build_export_metadata(
            snapshot,
            workspace_root=workspace_root,
            redaction_context=redaction_context,
        ),
        lineage=_build_export_lineage(snapshot, redaction_context),
        handoff=_build_export_handoff(
            snapshot,
            events,
            redaction_context,
            exported_by=exported_by,
            expected_custodian=expected_custodian,
            note=note,
        ),
        transcript=_export_transcript(snapshot.transcript, redaction_context),
        active_tool_calls=snapshot.active_tool_calls,
        pending_approvals=_redact_pending_approvals(
            snapshot.pending_approvals,
            redaction_context,
        ),
        turn_metrics=snapshot.turn_metrics,
        artifact_references=_artifact_references(events, redaction_context),
        event_count=len(events),
        events=[_event_summary(event) for event in events],
        redaction_notes=list(_REDACTION_NOTES),
    )


class _RedactionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_root: Path


def _build_export_metadata(
    snapshot: SessionSnapshotView,
    *,
    workspace_root: Path,
    redaction_context: _RedactionContext,
) -> SessionExportMetadata:
    return SessionExportMetadata(
        session_id=snapshot.session_id,
        status=snapshot.status,
        model_name=_redact_text(snapshot.model_name, redaction_context),
        approval_mode=snapshot.approval_mode,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        last_sequence=snapshot.last_sequence,
        workspace=SessionExportWorkspace(label=workspace_root.resolve().name),
    )


def _build_export_lineage(
    snapshot: SessionSnapshotView,
    redaction_context: _RedactionContext,
) -> SessionExportLineage:
    return SessionExportLineage(
        parent_session_id=snapshot.parent_session_id,
        forked_from_turn_id=_stringify_optional(snapshot.forked_from_turn_id),
        forked_from_sequence=snapshot.forked_from_sequence,
        branch_label=_redact_optional_text(snapshot.branch_label, redaction_context),
        child_sessions=_redact_child_sessions(
            snapshot.child_sessions,
            redaction_context,
        ),
        branchable_turns=_redact_branchable_turns(
            snapshot.branchable_turns,
            redaction_context,
        ),
        can_fork=snapshot.can_fork,
        latest_fork_point_turn_id=_stringify_optional(
            snapshot.latest_fork_point_turn_id
        ),
        latest_fork_point_sequence=snapshot.latest_fork_point_sequence,
        fork_blocked_reason=_redact_optional_text(
            snapshot.fork_blocked_reason,
            redaction_context,
        ),
    )


def _build_export_handoff(
    snapshot: SessionSnapshotView,
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
    *,
    exported_by: str | None,
    expected_custodian: str | None,
    note: str | None,
) -> SessionExportHandoff:
    return SessionExportHandoff(
        exported_by=_redact_optional_text(exported_by, redaction_context),
        expected_custodian=_redact_optional_text(
            expected_custodian,
            redaction_context,
        ),
        note=_redact_optional_text(note, redaction_context),
        last_actor_hint=_last_actor_hint(events, redaction_context),
        next_action_summary=_session_next_action_summary(snapshot),
        pending_approval_id=snapshot.pending_approval_id,
        pending_question_id=snapshot.pending_question_id,
        pending_question_text=_redact_optional_text(
            snapshot.pending_question_text,
            redaction_context,
        ),
        session_failure_message=_redact_optional_text(
            snapshot.session_failure_message,
            redaction_context,
        ),
        session_failure_retryable=snapshot.session_failure_retryable,
        historical_only=snapshot.status in {"completed", "failed", "cancelled"},
        live_actionable=snapshot.status
        in {"running", "awaiting_approval", "awaiting_user_input"},
    )


def _export_transcript(
    transcript: Sequence[TranscriptMessage],
    redaction_context: _RedactionContext,
) -> list[SessionExportTranscriptMessage]:
    return [
        SessionExportTranscriptMessage(
            message_id=str(message.message_id),
            role=message.role,
            parts=[
                MessagePart(
                    kind=part.kind,
                    text=_redact_text(part.text, redaction_context),
                )
                for part in message.parts
            ],
            created_at=message.created_at,
        )
        for message in transcript
    ]


def _redact_pending_approvals(
    approvals: Sequence[ApprovalRecord],
    redaction_context: _RedactionContext,
) -> list[ApprovalRecord]:
    return [
        approval.model_copy(
            update={
                "subject": _redact_text(approval.subject, redaction_context),
                "reason": _redact_text(approval.reason, redaction_context),
                "policy_source_label": _redact_optional_text(
                    approval.policy_source_label,
                    redaction_context,
                ),
                "decided_by": _redact_optional_text(
                    approval.decided_by,
                    redaction_context,
                ),
            }
        )
        for approval in approvals
    ]


def _redact_child_sessions(
    child_sessions: Sequence[ChildSessionSummaryView],
    redaction_context: _RedactionContext,
) -> list[ChildSessionSummaryView]:
    return [
        child.model_copy(
            update={
                "branch_label": _redact_optional_text(
                    child.branch_label,
                    redaction_context,
                ),
                "latest_message_summary": _redact_optional_text(
                    child.latest_message_summary,
                    redaction_context,
                ),
            }
        )
        for child in child_sessions
    ]


def _redact_branchable_turns(
    branchable_turns: Sequence[BranchableTurnView],
    redaction_context: _RedactionContext,
) -> list[BranchableTurnView]:
    return [
        turn.model_copy(update={"label": _redact_text(turn.label, redaction_context)})
        for turn in branchable_turns
    ]


def _artifact_references(
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
) -> list[SessionExportArtifactReference]:
    references: list[SessionExportArtifactReference] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, ToolArtifactRecorded | ReplayArtifactRecorded):
            continue
        references.append(
            SessionExportArtifactReference(
                sequence=event.sequence,
                event_type=event.event_type,
                turn_id=_stringify_optional(payload.turn_id),
                tool_call_id=_stringify_optional(payload.tool_call_id),
                artifact_kind=payload.artifact_kind,
                path=_portable_artifact_path(payload.path, redaction_context),
                content_sha256=payload.content_sha256,
                size_bytes=payload.size_bytes,
            )
        )
    return references


def _event_summary(event: EventEnvelope) -> SessionExportEventSummary:
    return SessionExportEventSummary(
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        turn_id=_stringify_optional(event.turn_id),
        message_id=_stringify_optional(event.message_id),
        tool_call_id=_stringify_optional(event.tool_call_id),
        approval_id=_stringify_optional(event.approval_id),
    )


def _session_next_action_summary(snapshot: SessionSnapshotView) -> str:
    if snapshot.projection_health.degraded:
        return "Rebuild derived projections from canonical events"
    if snapshot.status == "awaiting_user_input":
        return "Answer pending question"
    if snapshot.status == "awaiting_approval":
        return "Resolve pending approval"
    if snapshot.status == "running":
        if snapshot.current_turn_id is None:
            return "Send the next prompt or attach to continue live work"
        return "Wait for the current turn to finish or attach for live updates"
    if snapshot.status == "failed":
        return "Review failed session and decide whether to fork or retry"
    if snapshot.status == "completed":
        return "Inspect historical session or fork from a stable turn"
    return "Inspect session state"


def _last_actor_hint(
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
) -> str | None:
    for event in reversed(events):
        if isinstance(event.payload, ApprovalResolved):
            return _redact_text(event.payload.decided_by, redaction_context)
    return None


def _portable_artifact_path(
    path: str | None,
    redaction_context: _RedactionContext,
) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return _redact_text(path, redaction_context)
    if ".." in candidate.parts:
        return _REDACTION_PLACEHOLDER
    return _redact_text(path, redaction_context)


def _redact_optional_text(
    value: str | None,
    redaction_context: _RedactionContext,
) -> str | None:
    if value is None:
        return None
    return _redact_text(value, redaction_context)


def _redact_text(value: str, redaction_context: _RedactionContext) -> str:
    redacted = value.replace(
        str(redaction_context.workspace_root), _WORKSPACE_PLACEHOLDER
    )
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(_secret_replacement, redacted)
    return redacted


def _secret_replacement(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex >= 2:
        return f"{match.group(1)}={_REDACTION_PLACEHOLDER}"
    return _REDACTION_PLACEHOLDER


def _stringify_optional(value) -> str | None:
    if value is None:
        return None
    return str(value)
