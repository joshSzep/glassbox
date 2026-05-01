"""Portable session export for review and handoff workflows."""

import json
import re
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.ids import SessionId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import TranscriptMessage
from glassbox.runtime import session_export_models
from glassbox.runtime.branch_decision_support import BranchSearchDecisionSupport
from glassbox.runtime.branch_decision_support import (
    derive_branch_search_decision_support,
)
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.branch_search import BranchSearchRepository
from glassbox.runtime.knowledge_posture import WorkspaceKnowledgePosture
from glassbox.runtime.knowledge_posture import build_workspace_knowledge_posture
from glassbox.runtime.session_export_models import SessionExportArtifactReference
from glassbox.runtime.session_export_models import SessionExportBranchSearchSummary
from glassbox.runtime.session_export_models import SessionExportCheckpointEventReference
from glassbox.runtime.session_export_models import SessionExportEventSummary
from glassbox.runtime.session_export_models import SessionExportHandoff
from glassbox.runtime.session_export_models import SessionExportHandoffSummary
from glassbox.runtime.session_export_models import SessionExportLineage
from glassbox.runtime.session_export_models import SessionExportMetadata
from glassbox.runtime.session_export_models import SessionExportPayload
from glassbox.runtime.session_export_models import SessionExportPolicyDecision
from glassbox.runtime.session_export_models import SessionExportTaskEventReference
from glassbox.runtime.session_export_models import SessionExportTaskStepSummary
from glassbox.runtime.session_export_models import SessionExportTaskSummary
from glassbox.runtime.session_export_models import SessionExportTaskVerificationSummary
from glassbox.runtime.session_export_models import SessionExportTranscriptMessage
from glassbox.runtime.session_export_models import SessionExportWorkspace
from glassbox.runtime.session_queries import BranchableTurnView
from glassbox.runtime.session_queries import ChildSessionSummaryView
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

SESSION_EXPORT_KIND = session_export_models.SESSION_EXPORT_KIND
SESSION_EXPORT_VERSION = session_export_models.SESSION_EXPORT_VERSION

__all__ = [
    "SESSION_EXPORT_KIND",
    "SESSION_EXPORT_VERSION",
    "SessionExportPayload",
    "SessionExportTranscriptMessage",
    "build_session_export_payload",
    "export_session_package",
]

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
    task_query_service = TaskQueryService(
        cast(TaskPlanRepository, session_repository),
        workspace_root=workspace_root,
    )
    branch_search_service = BranchSearchQueryService(
        cast(BranchSearchRepository, session_repository)
    )
    snapshot = query_service.get_session_snapshot(session_id, turn_metrics_limit=25)
    events = session_repository.read_session_events(session_id)
    redaction_context = _RedactionContext(workspace_root=workspace_root.resolve())
    checkpoint_history = _redact_checkpoints(
        session_repository.list_task_checkpoints(session_id),
        redaction_context,
    )
    task_details = [
        task_query_service.get_task_detail(task.task_id)
        for task in task_query_service.list_task_summaries(session_id=session_id)
    ]
    compactions = session_repository.list_context_compactions(session_id, limit=None)
    branch_search_summaries = _branch_search_summaries(
        branch_search_service,
        session_id,
    )
    knowledge_posture = build_workspace_knowledge_posture(
        workspace_root,
        session_repository,
    )

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
            latest_checkpoint=checkpoint_history[0] if checkpoint_history else None,
            exported_by=exported_by,
            expected_custodian=expected_custodian,
            note=note,
            summary=_build_handoff_summary(
                snapshot=snapshot,
                task_details=task_details,
                compactions=compactions,
                branch_search_summaries=branch_search_summaries,
                knowledge_posture=knowledge_posture,
                redaction_context=redaction_context,
            ),
        ),
        autonomy_budget_posture=snapshot.budget_posture,
        transcript=_export_transcript(snapshot.transcript, redaction_context),
        active_tool_calls=snapshot.active_tool_calls,
        pending_approvals=_redact_pending_approvals(
            snapshot.pending_approvals,
            redaction_context,
        ),
        turn_metrics=snapshot.turn_metrics,
        artifact_references=_artifact_references(events, redaction_context),
        policy_decisions=_policy_decisions(events, redaction_context),
        task_summaries=_task_summaries(task_details, redaction_context),
        task_step_summaries=_task_step_summaries(task_details, redaction_context),
        task_verification_summaries=_task_verification_summaries(
            task_details,
            redaction_context,
        ),
        task_event_references=_task_event_references(events, redaction_context),
        checkpoint_history=checkpoint_history,
        checkpoint_event_references=_checkpoint_event_references(
            events,
            redaction_context,
        ),
        branch_search_summaries=branch_search_summaries,
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
    latest_checkpoint: TaskCheckpointRecord | None,
    exported_by: str | None,
    expected_custodian: str | None,
    note: str | None,
    summary: SessionExportHandoffSummary,
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
        latest_checkpoint=latest_checkpoint,
        summary=summary,
        historical_only=snapshot.status in {"completed", "failed", "cancelled"},
        live_actionable=snapshot.status
        in {"running", "awaiting_approval", "awaiting_user_input"},
    )


def _build_handoff_summary(
    *,
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    compactions: Sequence[ContextCompactionRecord],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    knowledge_posture: WorkspaceKnowledgePosture,
    redaction_context: _RedactionContext,
) -> SessionExportHandoffSummary:
    return SessionExportHandoffSummary(
        latest_objective=_latest_objective(
            snapshot,
            task_details,
            branch_search_summaries,
            redaction_context,
        ),
        checkpoint_posture=_checkpoint_posture(snapshot, redaction_context),
        compaction_posture=_compaction_posture(compactions),
        verification_state=_verification_state(task_details),
        accepted_risks=_accepted_risks_for_handoff(
            task_details,
            compactions,
            branch_search_summaries,
            redaction_context,
        ),
        pending_actions=_pending_actions_for_handoff(
            snapshot,
            task_details,
            branch_search_summaries,
            redaction_context,
        ),
        branch_lineage=_branch_lineage(
            snapshot,
            branch_search_summaries,
            redaction_context,
        ),
        knowledge_posture=_knowledge_posture_summary(knowledge_posture),
        safe_inspection_commands=_safe_inspection_commands(
            snapshot,
            task_details,
            branch_search_summaries,
        ),
    )


def _latest_objective(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: _RedactionContext,
) -> str:
    if snapshot.latest_checkpoint is not None:
        return _redact_text(snapshot.latest_checkpoint.objective, redaction_context)
    if task_details:
        latest_task = max(task_details, key=lambda detail: detail.task.updated_at)
        return _redact_text(latest_task.task.goal, redaction_context)
    if branch_search_summaries:
        latest_search = max(
            branch_search_summaries,
            key=lambda summary: summary.search.updated_at,
        )
        return _redact_text(latest_search.search.objective, redaction_context)
    for message in reversed(snapshot.transcript):
        if _enum_value(message.role) != "user":
            continue
        text = _message_text(message.parts)
        if text:
            return _redact_text(text, redaction_context)
    return "Inspect session state and decide the next safe action."


def _checkpoint_posture(
    snapshot: SessionSnapshotView,
    redaction_context: _RedactionContext,
) -> str:
    checkpoint = snapshot.latest_checkpoint
    if checkpoint is not None:
        status = checkpoint.verification_status or checkpoint.budget_status or "unknown"
        return _redact_text(
            "Latest checkpoint "
            f"{checkpoint.checkpoint_id} covers events "
            f"{checkpoint.source_start_sequence}-{checkpoint.source_end_sequence}; "
            f"status {status}; next action: {checkpoint.next_action}",
            redaction_context,
        )
    absence = snapshot.checkpoint_absence
    if absence is not None:
        return _redact_text(
            "No checkpoint: "
            f"{_enum_value(absence.reason)} ({absence.severity}); "
            f"{absence.message}; next action: {absence.next_action}",
            redaction_context,
        )
    return (
        "No checkpoint evidence is projected; inspect session status before continuing."
    )


def _compaction_posture(compactions: Sequence[ContextCompactionRecord]) -> str:
    if not compactions:
        return "No context compaction artifacts are retained for this session."
    stale_count = sum(
        1 for compaction in compactions if _enum_value(compaction.freshness) != "fresh"
    )
    accepted_risk_count = sum(
        compaction.accepted_risk_count for compaction in compactions
    )
    latest = max(compactions, key=lambda compaction: compaction.last_sequence)
    stale_fragment = f"{stale_count} stale" if stale_count else "all fresh"
    risk_fragment = (
        f"; {accepted_risk_count} accepted risk(s)" if accepted_risk_count else ""
    )
    return (
        f"{len(compactions)} retained context compaction(s), {stale_fragment}; "
        f"latest covers events {latest.source_start_sequence}-"
        f"{latest.source_end_sequence} ({_enum_value(latest.freshness)})"
        f"{risk_fragment}."
    )


def _verification_state(task_details: Sequence[TaskDetailView]) -> str:
    if not task_details:
        return "No task plans are retained, so task verification state is absent."
    total = sum(detail.verification_summary.total_count for detail in task_details)
    if total == 0:
        return (
            f"{len(task_details)} task plan(s) retained with no verification "
            "checks yet."
        )
    passed = sum(detail.verification_summary.passed_count for detail in task_details)
    failed = sum(detail.verification_summary.failed_count for detail in task_details)
    running = sum(detail.verification_summary.running_count for detail in task_details)
    skipped = sum(detail.verification_summary.skipped_count for detail in task_details)
    accepted = sum(
        detail.verification_summary.accepted_risk_count for detail in task_details
    )
    postures = _dedupe(
        detail.verification_summary.current_posture for detail in task_details
    )
    return (
        f"{len(task_details)} task plan(s), {total} verification check(s): "
        f"{passed} passed, {failed} failed, {running} running, {skipped} skipped, "
        f"{accepted} accepted risk(s); posture {', '.join(postures)}."
    )


def _accepted_risks_for_handoff(
    task_details: Sequence[TaskDetailView],
    compactions: Sequence[ContextCompactionRecord],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: _RedactionContext,
) -> list[str]:
    risks: list[str] = []
    for detail in task_details:
        for ledger_entry in detail.verification_ledger:
            risks.extend(ledger_entry.accepted_risks)
            if ledger_entry.residual_risk_reason is not None:
                risks.append(ledger_entry.residual_risk_reason)
    compaction_risk_count = sum(
        compaction.accepted_risk_count for compaction in compactions
    )
    if compaction_risk_count:
        risks.append(
            f"{compaction_risk_count} accepted context compaction risk(s) retained"
        )
    for support in _branch_support(branch_search_summaries):
        for candidate in support.candidates:
            risks.extend(candidate.accepted_risks)
    return _dedupe(_redact_text(risk, redaction_context) for risk in risks if risk)[:20]


def _pending_actions_for_handoff(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: _RedactionContext,
) -> list[str]:
    actions = [_session_next_action_summary(snapshot)]
    if snapshot.pending_approval_id is not None:
        actions.append(f"Inspect pending approval {snapshot.pending_approval_id}.")
    if snapshot.pending_question_text is not None:
        actions.append(f"Answer pending question: {snapshot.pending_question_text}")
    if snapshot.session_failure_message is not None:
        actions.append(f"Inspect session failure: {snapshot.session_failure_message}")
    if snapshot.latest_checkpoint is not None:
        actions.append(snapshot.latest_checkpoint.next_action)
    for detail in sorted(
        task_details,
        key=lambda item: item.task.updated_at,
        reverse=True,
    )[:3]:
        actions.append(detail.task.next_action_summary)
    for support in _branch_support(branch_search_summaries):
        for candidate in support.candidates:
            if candidate.recommended_follow_up_action:
                actions.append(candidate.recommended_follow_up_action)
    return _dedupe(
        _redact_text(action, redaction_context) for action in actions if action
    )[:20]


def _branch_lineage(
    snapshot: SessionSnapshotView,
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: _RedactionContext,
) -> str:
    if snapshot.parent_session_id is not None:
        lineage = (
            f"Branch session from parent {snapshot.parent_session_id}"
            f" at sequence {snapshot.forked_from_sequence or 'unknown'}"
        )
        if snapshot.branch_label:
            lineage = f"{lineage} ({snapshot.branch_label})"
    else:
        lineage = "Root session"
    if snapshot.child_sessions:
        lineage = f"{lineage}; {len(snapshot.child_sessions)} child session(s)"
    if snapshot.can_fork:
        lineage = (
            f"{lineage}; forkable at sequence "
            f"{snapshot.latest_fork_point_sequence or 'unknown'}"
        )
    elif snapshot.fork_blocked_reason:
        lineage = f"{lineage}; fork blocked: {snapshot.fork_blocked_reason}"
    if branch_search_summaries:
        selected_count = sum(
            1
            for summary in branch_search_summaries
            if summary.search.selected_candidate_id is not None
        )
        lineage = (
            f"{lineage}; {len(branch_search_summaries)} branch search(es), "
            f"{selected_count} with selected candidate"
        )
    return _redact_text(lineage, redaction_context)


def _knowledge_posture_summary(posture: WorkspaceKnowledgePosture) -> str:
    cue_fragments = [f"{cue.key}={cue.status}" for cue in posture.cues[:6]]
    return f"Overall {posture.overall_status}; " + ", ".join(cue_fragments)


def _safe_inspection_commands(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
) -> list[str]:
    commands = [
        f"glassbox session status {snapshot.session_id} --cwd .",
        f"glassbox session compactions {snapshot.session_id} --cwd .",
        "glassbox observability status --cwd .",
        "glassbox eval audit --cwd .",
    ]
    commands.extend(
        f"glassbox task show {detail.task.task_id} --cwd ."
        for detail in sorted(
            task_details,
            key=lambda item: item.task.updated_at,
            reverse=True,
        )[:3]
    )
    commands.extend(
        f"glassbox branch-search show {summary.search.search_id} --cwd ."
        for summary in branch_search_summaries[:3]
    )
    return _dedupe(commands)[:20]


def _branch_support(
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
) -> list[BranchSearchDecisionSupport]:
    return [
        derive_branch_search_decision_support(
            search=summary.search,
            candidates=summary.candidates,
        )
        for summary in branch_search_summaries
    ]


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


def _policy_decisions(
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
) -> list[SessionExportPolicyDecision]:
    decisions: list[SessionExportPolicyDecision] = []
    for event in events:
        payload = event.payload
        if not isinstance(
            payload,
            ModelToolCallRequested | ToolExecutionStarted | ApprovalRequested,
        ):
            continue
        trace = _policy_trace(payload)
        if trace is None:
            continue
        decisions.append(
            SessionExportPolicyDecision(
                sequence=event.sequence,
                event_type=event.event_type,
                turn_id=_stringify_optional(payload.turn_id),
                tool_call_id=_stringify_optional(
                    getattr(payload, "tool_call_id", None)
                ),
                approval_id=_stringify_optional(getattr(payload, "approval_id", None)),
                tool_name=_redact_optional_text(
                    getattr(payload, "tool_name", None),
                    redaction_context,
                ),
                subject=_redact_optional_text(
                    getattr(payload, "subject", None),
                    redaction_context,
                ),
                trace=trace.model_copy(
                    update={
                        "source_label": _redact_text(
                            trace.source_label,
                            redaction_context,
                        ),
                        "reason": _redact_text(trace.reason, redaction_context),
                    }
                ),
            )
        )
    return decisions


def _policy_trace(
    payload: ModelToolCallRequested | ToolExecutionStarted | ApprovalRequested,
) -> PolicyDecisionTrace | None:
    if payload.policy_trace is not None:
        return payload.policy_trace

    reason = (
        payload.reason
        if isinstance(payload, ApprovalRequested)
        else payload.policy_reason
    )
    if (
        payload.policy_outcome is None
        or payload.policy_risk_level is None
        or payload.policy_source_kind is None
        or payload.policy_source_label is None
        or reason is None
    ):
        return None

    return PolicyDecisionTrace(
        outcome=payload.policy_outcome,
        risk_level=payload.policy_risk_level,
        source_kind=payload.policy_source_kind,
        source_label=payload.policy_source_label,
        reason=reason,
    )


def _task_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: _RedactionContext,
) -> list[SessionExportTaskSummary]:
    return [
        SessionExportTaskSummary(
            task_id=detail.task.task_id,
            title=_redact_text(detail.task.title, redaction_context),
            goal=_redact_text(detail.task.goal, redaction_context),
            status=detail.task.status.value,
            updated_at=detail.task.updated_at,
            blocked_reason=(
                None
                if detail.task.blocked_reason is None
                else detail.task.blocked_reason.value
            ),
            blocked_detail=_redact_optional_text(
                detail.task.blocked_detail,
                redaction_context,
            ),
            current_step_id=detail.task.current_step_id,
            step_count=detail.task.step_count,
            next_action_summary=_redact_text(
                detail.task.next_action_summary,
                redaction_context,
            ),
        )
        for detail in task_details
    ]


def _task_step_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: _RedactionContext,
) -> list[SessionExportTaskStepSummary]:
    summaries: list[SessionExportTaskStepSummary] = []
    for detail in task_details:
        summaries.extend(
            SessionExportTaskStepSummary(
                task_id=detail.task.task_id,
                step_id=step.step_id,
                title=_redact_text(step.title, redaction_context),
                order=step.order,
                status=step.status.value,
                description=_redact_optional_text(
                    step.description,
                    redaction_context,
                ),
                blocked_reason=(
                    None if step.blocked_reason is None else step.blocked_reason.value
                ),
            )
            for step in detail.steps
        )
    return summaries


def _task_verification_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: _RedactionContext,
) -> list[SessionExportTaskVerificationSummary]:
    summaries: list[SessionExportTaskVerificationSummary] = []
    for detail in task_details:
        summaries.extend(
            SessionExportTaskVerificationSummary(
                task_id=detail.task.task_id,
                verification_id=verification.verification_id,
                check_name=_redact_text(verification.check_name, redaction_context),
                status=verification.status.value,
                step_id=verification.step_id,
                summary=_redact_optional_text(
                    verification.summary,
                    redaction_context,
                ),
            )
            for verification in detail.verifications
        )
    return summaries


def _redact_checkpoints(
    checkpoints: Sequence[TaskCheckpointRecord],
    redaction_context: _RedactionContext,
) -> list[TaskCheckpointRecord]:
    return [
        checkpoint.model_copy(
            update={
                "objective": _redact_text(checkpoint.objective, redaction_context),
                "completed_step": _redact_optional_text(
                    checkpoint.completed_step,
                    redaction_context,
                ),
                "next_action": _redact_text(
                    checkpoint.next_action,
                    redaction_context,
                ),
                "blockers": [
                    _redact_text(blocker, redaction_context)
                    for blocker in checkpoint.blockers
                ],
                "touched_files": [
                    _redact_text(path, redaction_context)
                    for path in checkpoint.touched_files
                ],
                "recovery_guidance": _redact_text(
                    checkpoint.recovery_guidance,
                    redaction_context,
                ),
            }
        )
        for checkpoint in checkpoints
    ]


def _task_event_references(
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
) -> list[SessionExportTaskEventReference]:
    references: list[SessionExportTaskEventReference] = []
    for event in events:
        if event.task_id is None:
            continue
        if isinstance(event.payload, TaskCheckpointCreated):
            continue
        references.append(
            SessionExportTaskEventReference(
                sequence=event.sequence,
                event_type=event.event_type,
                created_at=event.created_at,
                task_id=event.task_id,
                turn_id=_stringify_optional(event.turn_id),
                payload=cast(
                    dict[str, object],
                    _redact_json_value(
                        event.payload.model_dump(mode="json"),
                        redaction_context,
                    ),
                ),
            )
        )
    return references


def _checkpoint_event_references(
    events: Sequence[EventEnvelope],
    redaction_context: _RedactionContext,
) -> list[SessionExportCheckpointEventReference]:
    references: list[SessionExportCheckpointEventReference] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskCheckpointCreated):
            continue
        references.append(
            SessionExportCheckpointEventReference(
                sequence=event.sequence,
                event_type=event.event_type,
                created_at=event.created_at,
                checkpoint_id=payload.checkpoint_id,
                task_id=payload.task_id,
                turn_id=_stringify_optional(payload.turn_id),
                payload=cast(
                    dict[str, object],
                    _redact_json_value(
                        payload.model_dump(mode="json"),
                        redaction_context,
                    ),
                ),
            )
        )
    return references


def _branch_search_summaries(
    branch_search_service: BranchSearchQueryService,
    session_id: SessionId,
) -> list[SessionExportBranchSearchSummary]:
    summaries: list[SessionExportBranchSearchSummary] = []
    for search in branch_search_service.list_searches(session_id=session_id):
        detail = branch_search_service.get_detail(search.search_id)
        summaries.append(
            SessionExportBranchSearchSummary(
                search=detail.search,
                candidates=detail.candidates,
            )
        )
    return summaries


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
    if snapshot.budget_posture is not None:
        budget_action = _budget_export_next_action(snapshot.budget_posture)
        if budget_action is not None:
            return budget_action
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


def _budget_export_next_action(budget_posture) -> str | None:
    if budget_posture.last_reason is None:
        return None
    if budget_posture.last_reason == "budget_exhausted":
        return "Review budget exhaustion and choose a smaller next step or override"
    if budget_posture.last_reason == "policy_blocked":
        return "Review policy block before continuing"
    if budget_posture.last_reason == "verification_failed":
        return "Review failed verification before continuing"
    if budget_posture.last_reason == "approval_required":
        return "Resolve pending approval"
    return None


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


def _redact_json_value(value: Any, redaction_context: _RedactionContext) -> Any:
    if isinstance(value, str):
        return _redact_text(value, redaction_context)
    if isinstance(value, list):
        return [_redact_json_value(item, redaction_context) for item in value]
    if isinstance(value, dict):
        return {
            key: _redact_json_value(item, redaction_context)
            for key, item in value.items()
        }
    return value


def _secret_replacement(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex >= 2:
        return f"{match.group(1)}={_REDACTION_PLACEHOLDER}"
    return _REDACTION_PLACEHOLDER


def _message_text(parts: Sequence[MessagePart]) -> str:
    return " ".join(part.text for part in parts if part.text).strip()


def _enum_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _stringify_optional(value) -> str | None:
    if value is None:
        return None
    return str(value)
