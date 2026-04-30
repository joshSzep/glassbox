"""Pure extraction helpers for review-gated workspace memory candidates."""

import json
from collections.abc import Sequence
from typing import Protocol

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import WorkspaceMemoryCandidateRejected
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.ids import SessionId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType
from glassbox.runtime.workspace_memory_candidates import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_candidates import ModelMemorySuggestion
from glassbox.runtime.workspace_memory_candidates import WorkspaceMemoryCandidate
from glassbox.runtime.workspace_memory_candidates import build_candidate
from glassbox.runtime.workspace_memory_candidates import summarize_candidate_content
from glassbox.runtime.workspace_memory_redaction import redact_sensitive_text

_TASK_OUTCOME_STATUSES = {
    TaskPlanStatus.COMPLETED,
    TaskPlanStatus.FAILED,
    TaskPlanStatus.CANCELLED,
    TaskPlanStatus.ABANDONED,
}

_STABLE_COMMAND_PREFIXES = (
    "uv run ",
    "pnpm ",
    "npm test",
    "pytest",
    "make ",
    "glassbox ",
)


class WorkspaceMemoryExtractionRepository(Protocol):
    """Repository reads needed to propose workspace memory candidates."""

    def list_runtime_notes(
        self,
        session_id: SessionId,
        *,
        include_inherited: bool = True,
    ) -> list[RuntimeNoteRecord]: ...

    def list_tasks(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskRecord]: ...

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...


def runtime_note_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for note in repository.list_runtime_notes(
        session_id,
        include_inherited=False,
    ):
        content, redacted = redact_sensitive_text(note.message)
        kind = _kind_for_runtime_note(note)
        summary = summarize_candidate_content(content)
        provenance = WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
            session_id=session_id,
            source_sequence=note.source_sequence,
            source_label=f"runtime_note:{note.category}",
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=kind,
                content=content,
                summary=summary,
                provenance=provenance,
                tags=["runtime-note", note.category],
                redacted=redacted,
                source_label=f"runtime note {note.source_sequence}",
                created_at=note.created_at,
            )
        )
    return candidates


def task_outcome_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for task in repository.list_tasks(session_id=session_id):
        if task.status not in _TASK_OUTCOME_STATUSES:
            continue
        detail = f" Task detail: {task.blocked_detail}" if task.blocked_detail else ""
        content, redacted = redact_sensitive_text(
            f"Task '{task.title}' finished with status {task.status.value}. "
            f"Goal: {task.goal}.{detail}"
        )
        provenance = WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.TASK,
            task_id=task.task_id,
            source_label="task outcome",
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.TASK_OUTCOME,
                content=content,
                summary=summarize_candidate_content(content),
                provenance=provenance,
                tags=["task", task.status.value],
                redacted=redacted,
                source_label=f"task {task.task_id}",
                created_at=task.updated_at,
            )
        )
    return candidates


def stable_command_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    events = repository.read_session_events(session_id)
    requests = _tool_requests_by_id(events)
    candidates: list[WorkspaceMemoryCandidate] = []
    seen_commands: set[str] = set()
    for event in events:
        payload = event.payload
        if not isinstance(payload, ToolExecutionCompleted) or not payload.success:
            continue
        request = requests.get(payload.tool_call_id)
        if request is None or request.tool_name != "run_command":
            continue
        command = _command_argument(request.arguments_json)
        if command is None or not _is_stable_command(command):
            continue
        normalized_command = " ".join(command.split())
        if normalized_command in seen_commands:
            continue
        seen_commands.add(normalized_command)
        content, redacted = redact_sensitive_text(
            f"Stable local command: {normalized_command}"
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.COMMAND,
                content=content,
                summary=f"Stable command: {normalized_command}",
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.TOOL_RESULT,
                    tool_call_id=payload.tool_call_id,
                    source_label="successful command",
                ),
                tags=["command", "automatic"],
                redacted=redacted,
                source_label=f"tool {payload.tool_call_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def repeated_failure_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    buckets: dict[str, list[tuple[EventEnvelope, ToolExecutionCompleted]]] = {}
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if isinstance(payload, ToolExecutionCompleted) and not payload.success:
            key = summarize_candidate_content(payload.summary).casefold()
            buckets.setdefault(key, []).append((event, payload))
    candidates: list[WorkspaceMemoryCandidate] = []
    for failures in buckets.values():
        if len(failures) < 2:
            continue
        event, payload = failures[-1]
        content, redacted = redact_sensitive_text(
            f"Repeated tool failure observed {len(failures)} times: {payload.summary}"
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.FAILURE_PATTERN,
                content=content,
                summary=(
                    f"Repeated failure: {summarize_candidate_content(payload.summary)}"
                ),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.TOOL_RESULT,
                    tool_call_id=payload.tool_call_id,
                    source_label="repeated tool failure",
                ),
                tags=["failure-pattern", "automatic"],
                redacted=redacted,
                source_label=f"tool {payload.tool_call_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def confirmed_fix_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    events = repository.read_session_events(session_id)
    approved_approvals = {
        payload.approval_id
        for payload in (event.payload for event in events)
        if isinstance(payload, ApprovalResolved)
        and getattr(payload.decision, "value", payload.decision) == "approved"
    }
    requests = {
        payload.tool_call_id: payload
        for payload in (event.payload for event in events)
        if isinstance(payload, ApprovalRequested)
        and payload.approval_id in approved_approvals
        and payload.tool_call_id is not None
    }
    candidates: list[WorkspaceMemoryCandidate] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, ToolExecutionCompleted) or not payload.success:
            continue
        approval = requests.get(payload.tool_call_id)
        if approval is None:
            continue
        content, redacted = redact_sensitive_text(
            f"Operator-approved fix completed for {approval.subject}. "
            f"Tool summary: {payload.summary}"
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.FACT,
                content=content,
                summary=(
                    "Approved fix completed: "
                    f"{summarize_candidate_content(approval.subject)}"
                ),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.TOOL_RESULT,
                    tool_call_id=payload.tool_call_id,
                    source_label="approved fix",
                ),
                tags=["confirmed-fix", "automatic"],
                redacted=redacted,
                source_label=f"approval {approval.approval_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def long_run_checkpoint_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if not isinstance(payload, TaskCheckpointCreated):
            continue
        fragments = [
            f"Long-run checkpoint objective: {payload.objective}.",
            f"Next action: {payload.next_action}.",
            f"Recovery guidance: {payload.recovery_guidance}.",
        ]
        if payload.completed_step:
            fragments.append(f"Completed step: {payload.completed_step}.")
        if payload.verification_status:
            fragments.append(f"Verification: {payload.verification_status}.")
        content, redacted = redact_sensitive_text(" ".join(fragments))
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.TASK_OUTCOME,
                content=content,
                summary=summarize_candidate_content(content),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    session_id=session_id,
                    source_sequence=event.sequence,
                    task_id=payload.task_id,
                    source_label="long-run checkpoint",
                    note=_artifact_note(payload.artifact_id),
                ),
                tags=["long-run", "checkpoint"],
                redacted=redacted,
                source_label=f"checkpoint {payload.checkpoint_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def long_run_compaction_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if not isinstance(payload, ContextCompactionCreated):
            continue
        if payload.freshness.value != "fresh":
            continue
        limitations = (
            " Limitations: " + "; ".join(payload.limitations)
            if payload.limitations
            else ""
        )
        content, redacted = redact_sensitive_text(
            f"Fresh context compaction: {payload.summary}.{limitations}"
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.ARCHITECTURE_NOTE,
                content=content,
                summary=summarize_candidate_content(content),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    session_id=session_id,
                    source_sequence=event.sequence,
                    task_id=payload.task_id,
                    artifact_id=payload.artifact_id,
                    source_label="context compaction",
                    note=_artifact_note(payload.artifact_id),
                ),
                tags=["long-run", "compaction", payload.scope.value],
                redacted=redacted,
                source_label=f"compaction {payload.compaction_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def long_run_verification_candidates(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    events = repository.read_session_events(session_id)
    planned = {
        payload.verification.verification_id: payload.verification
        for payload in (event.payload for event in events)
        if isinstance(payload, TaskVerificationPlanned)
    }
    return [
        *last_known_good_candidates(events, session_id, planned),
        *verification_failure_pattern_candidates(events, session_id),
        *accepted_residual_risk_candidates(events, session_id),
    ]


def last_known_good_candidates(
    events: list[EventEnvelope],
    session_id: SessionId,
    planned: dict,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskVerificationCompleted):
            continue
        if payload.status != TaskVerificationStatus.PASSED:
            continue
        plan = planned.get(payload.verification_id)
        command = " ".join(plan.command) if plan is not None else None
        check_label = plan.check_name if plan else str(payload.verification_id)
        content_parts = [f"Last known good verification passed: {check_label}."]
        if command:
            content_parts.append(f"Verified command: {command}.")
        if payload.summary:
            content_parts.append(f"Summary: {payload.summary}.")
        content, redacted = redact_sensitive_text(" ".join(content_parts))
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=(
                    WorkspaceMemoryKind.COMMAND if command else WorkspaceMemoryKind.FACT
                ),
                content=content,
                summary=summarize_candidate_content(content),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    session_id=session_id,
                    source_sequence=event.sequence,
                    task_id=payload.task_id,
                    artifact_id=payload.artifact_id,
                    source_label="last-known-good verification",
                    note=_artifact_note(payload.artifact_id),
                ),
                tags=["long-run", "last-known-good", "verification"],
                redacted=redacted,
                source_label=f"verification {payload.verification_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def verification_failure_pattern_candidates(
    events: list[EventEnvelope],
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    buckets: dict[str, list[tuple[EventEnvelope, TaskVerificationFailed]]] = {}
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskVerificationFailed):
            continue
        key = summarize_candidate_content(payload.failure.summary).casefold()
        buckets.setdefault(key, []).append((event, payload))

    candidates: list[WorkspaceMemoryCandidate] = []
    for failures in buckets.values():
        if len(failures) < 2:
            continue
        event, payload = failures[-1]
        content, redacted = redact_sensitive_text(
            "Repeated verification failure observed "
            f"{len(failures)} times: {payload.failure.summary}"
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.FAILURE_PATTERN,
                content=content,
                summary=(
                    "Repeated verification failure: "
                    f"{summarize_candidate_content(payload.failure.summary)}"
                ),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    session_id=session_id,
                    source_sequence=event.sequence,
                    task_id=payload.task_id,
                    artifact_id=payload.failure.artifact_id,
                    source_label="repeated verification failure",
                    note=_artifact_note(payload.failure.artifact_id),
                ),
                tags=["long-run", "failure-pattern", "verification"],
                redacted=redacted,
                source_label=f"verification {payload.verification_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def accepted_residual_risk_candidates(
    events: list[EventEnvelope],
    session_id: SessionId,
) -> list[WorkspaceMemoryCandidate]:
    candidates: list[WorkspaceMemoryCandidate] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskVerificationResidualRiskAccepted):
            continue
        risks = "; ".join(payload.residual_risks) or "unspecified residual risk"
        content, redacted = redact_sensitive_text(
            f"Accepted residual verification risk: {payload.reason}. Risks: {risks}."
        )
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=WorkspaceMemoryKind.FAILURE_PATTERN,
                content=content,
                summary=summarize_candidate_content(content),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    session_id=session_id,
                    source_sequence=event.sequence,
                    task_id=payload.task_id,
                    source_label="accepted residual risk",
                ),
                tags=["long-run", "accepted-risk", "verification"],
                redacted=redacted,
                source_label=f"verification {payload.verification_id}",
                created_at=event.created_at,
            )
        )
    return candidates


def model_assisted_candidates(
    session_id: SessionId,
    suggestions: Sequence[ModelMemorySuggestion],
    policy: MemoryExtractionPolicy,
) -> list[WorkspaceMemoryCandidate]:
    if not policy.allow_model_assisted:
        return []
    candidates: list[WorkspaceMemoryCandidate] = []
    for suggestion in suggestions:
        if suggestion.confidence < policy.min_model_confidence:
            continue
        content, redacted = redact_sensitive_text(suggestion.content)
        summary = suggestion.summary
        summary_redacted = False
        if summary is not None:
            summary, summary_redacted = redact_sensitive_text(summary)
        candidates.append(
            build_candidate(
                session_id=session_id,
                kind=suggestion.kind,
                content=content,
                summary=summary or summarize_candidate_content(content),
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.RUNTIME_NOTE,
                    source_label=suggestion.source_label,
                ),
                tags=["model-assisted", *suggestion.tags],
                redacted=redacted or summary_redacted,
                source_label=suggestion.source_label,
                created_at=None,
            )
        )
    return candidates


def excluded_candidate_ids(
    repository: WorkspaceMemoryExtractionRepository,
    session_id: SessionId,
) -> set[str]:
    excluded_ids: set[str] = set()
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if isinstance(payload, WorkspaceMemoryCandidateRejected):
            excluded_ids.add(payload.candidate_id)
        elif isinstance(payload, WorkspaceMemoryConfirmed):
            prefix = "confirmed candidate "
            if payload.reason is not None and payload.reason.startswith(prefix):
                excluded_ids.add(payload.reason.removeprefix(prefix))
    return excluded_ids


def _artifact_note(artifact_id) -> str | None:
    return f"artifact_id={artifact_id}" if artifact_id is not None else None


def _tool_requests_by_id(
    events: Sequence[EventEnvelope],
) -> dict[object, ModelToolCallRequested]:
    return {
        payload.tool_call_id: payload
        for payload in (event.payload for event in events)
        if isinstance(payload, ModelToolCallRequested)
    }


def _command_argument(arguments_json: str) -> str | None:
    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(arguments, dict):
        return None
    command = arguments.get("command")
    if not isinstance(command, str):
        return None
    normalized = " ".join(command.split())
    return normalized or None


def _is_stable_command(command: str) -> bool:
    normalized = command.casefold()
    return any(normalized.startswith(prefix) for prefix in _STABLE_COMMAND_PREFIXES)


def _kind_for_runtime_note(note: RuntimeNoteRecord) -> WorkspaceMemoryKind:
    if note.category.lower() in {"operator", "preference", "user"}:
        return WorkspaceMemoryKind.USER_PREFERENCE
    return WorkspaceMemoryKind.FACT


__all__ = [
    "confirmed_fix_candidates",
    "excluded_candidate_ids",
    "model_assisted_candidates",
    "repeated_failure_candidates",
    "runtime_note_candidates",
    "stable_command_candidates",
    "task_outcome_candidates",
]
