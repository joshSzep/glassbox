"""Operator-reviewed workspace memory capture helpers."""

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import WorkspaceMemoryCandidateRejected
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryCreated
from glassbox.core.events import WorkspaceMemoryUpdated
from glassbox.core.ids import SessionId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.ids import new_workspace_memory_id
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType

_SENSITIVE_ASSIGNMENT = re.compile(
    r"\b(api[_-]?key|password|secret|token)\b\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)
_LONG_SECRETISH_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")


class WorkspaceMemoryCaptureRepository(Protocol):
    """Repository methods used by the memory capture service."""

    def get_session(self, session_id: SessionId): ...

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

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...

    def append_events(self, events: Sequence[EventEnvelope]) -> list[EventEnvelope]: ...

    def get_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
    ) -> WorkspaceMemoryEntry | None: ...


class WorkspaceMemoryCandidate(BaseModel):
    """A deterministic, operator-reviewed memory proposal."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    session_id: SessionId
    kind: WorkspaceMemoryKind
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    provenance: WorkspaceMemoryProvenance
    tags: list[str] = Field(default_factory=list)
    redacted: bool = False
    source_label: str
    created_at: datetime | None = None


class ModelMemorySuggestion(BaseModel):
    """Model-proposed memory candidate text awaiting review."""

    model_config = ConfigDict(extra="forbid")

    kind: WorkspaceMemoryKind = WorkspaceMemoryKind.FACT
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    source_label: str = "model-assisted extraction"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class MemoryExtractionPolicy(BaseModel):
    """Review-gated controls for automatic memory candidate extraction."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_candidates: int | None = Field(default=None, ge=1)
    max_age_days: int = Field(default=30, ge=1)
    allow_model_assisted: bool = False
    min_model_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class WorkspaceMemoryCaptureService:
    """Generate and commit operator-confirmed workspace memory."""

    def __init__(self, repository: WorkspaceMemoryCaptureRepository) -> None:
        self._repository = repository

    def list_candidates(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
        policy: MemoryExtractionPolicy | None = None,
        model_suggestions: Sequence[ModelMemorySuggestion] = (),
        now: datetime | None = None,
    ) -> list[WorkspaceMemoryCandidate]:
        self._ensure_session_exists(session_id)
        extraction_policy = policy or MemoryExtractionPolicy(max_candidates=limit)
        if not extraction_policy.enabled:
            return []
        excluded_ids = self._excluded_candidate_ids(session_id)
        candidate_limit = limit or extraction_policy.max_candidates
        candidates = _dedupe_candidates(
            [
                candidate
                for candidate in [
                    *self._runtime_note_candidates(session_id),
                    *self._task_outcome_candidates(session_id),
                    *self._stable_command_candidates(session_id),
                    *self._repeated_failure_candidates(session_id),
                    *self._confirmed_fix_candidates(session_id),
                    *self._model_assisted_candidates(
                        session_id,
                        model_suggestions,
                        extraction_policy,
                    ),
                ]
                if candidate.candidate_id not in excluded_ids
                and _candidate_is_useful(candidate)
            ]
        )
        candidates = _filter_stale_candidates(
            candidates,
            now=now or datetime.now(UTC),
            max_age=timedelta(days=extraction_policy.max_age_days),
        )
        return candidates if candidate_limit is None else candidates[:candidate_limit]

    def list_model_assisted_candidates(
        self,
        session_id: SessionId,
        suggestions: Sequence[ModelMemorySuggestion],
        *,
        policy: MemoryExtractionPolicy | None = None,
    ) -> list[WorkspaceMemoryCandidate]:
        """Turn model suggestions into review-only candidates, never memory."""

        extraction_policy = policy or MemoryExtractionPolicy(allow_model_assisted=True)
        self._ensure_session_exists(session_id)
        if not extraction_policy.enabled:
            return []
        return _dedupe_candidates(
            [
                candidate
                for candidate in self._model_assisted_candidates(
                    session_id,
                    suggestions,
                    extraction_policy.model_copy(update={"allow_model_assisted": True}),
                )
                if _candidate_is_useful(candidate)
            ]
        )

    def confirm_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        *,
        confirmed_by: str = "operator",
        memory_id: WorkspaceMemoryId | None = None,
        kind: WorkspaceMemoryKind | None = None,
        content: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> WorkspaceMemoryEntry:
        candidate = self._require_candidate(session_id, candidate_id)
        resolved_memory_id = memory_id or new_workspace_memory_id()
        resolved_content, content_redacted = redact_sensitive_text(
            content or candidate.content
        )
        resolved_summary = summary if summary is not None else candidate.summary
        summary_redacted = False
        if resolved_summary is not None:
            resolved_summary, summary_redacted = redact_sensitive_text(resolved_summary)
        self._repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryCreated(
                        memory_id=resolved_memory_id,
                        kind=kind or candidate.kind,
                        content=resolved_content,
                        summary=resolved_summary,
                        provenance=candidate.provenance,
                        created_by=confirmed_by,
                        tags=tags if tags is not None else candidate.tags,
                        redacted=(
                            candidate.redacted or content_redacted or summary_redacted
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryConfirmed(
                        memory_id=resolved_memory_id,
                        confirmed_by=confirmed_by,
                        reason=f"confirmed candidate {candidate.candidate_id}",
                    ),
                ),
            ]
        )
        entry = self._repository.get_workspace_memory(resolved_memory_id)
        if entry is None:
            raise ValueError(
                f"workspace memory was not projected: {resolved_memory_id}"
            )
        return entry

    def merge_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        memory_id: WorkspaceMemoryId,
        *,
        merged_by: str = "operator",
    ) -> WorkspaceMemoryEntry:
        candidate = self._require_candidate(session_id, candidate_id)
        existing = self._repository.get_workspace_memory(memory_id)
        if existing is None:
            raise ValueError(f"unknown workspace memory: {memory_id}")
        self._repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryUpdated(
                        memory_id=memory_id,
                        updated_by=merged_by,
                        content=_merge_text(existing.content, candidate.content),
                        summary=existing.summary or candidate.summary,
                        tags=list(dict.fromkeys([*existing.tags, *candidate.tags])),
                        reason=f"merged candidate {candidate.candidate_id}",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryConfirmed(
                        memory_id=memory_id,
                        confirmed_by=merged_by,
                        reason=f"confirmed candidate {candidate.candidate_id}",
                    ),
                ),
            ]
        )
        entry = self._repository.get_workspace_memory(memory_id)
        if entry is None:
            raise ValueError(f"workspace memory was not projected: {memory_id}")
        return entry

    def reject_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        *,
        rejected_by: str = "operator",
        reason: str,
    ) -> WorkspaceMemoryCandidate:
        candidate = self._require_candidate(session_id, candidate_id)
        self._repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorkspaceMemoryCandidateRejected(
                    candidate_id=candidate.candidate_id,
                    kind=candidate.kind,
                    content_summary=candidate.summary or candidate.content[:500],
                    provenance=candidate.provenance,
                    rejected_by=rejected_by,
                    reason=reason,
                    redacted=candidate.redacted,
                ),
            )
        )
        return candidate

    def add_operator_memory(
        self,
        session_id: SessionId,
        *,
        kind: WorkspaceMemoryKind,
        content: str,
        summary: str | None = None,
        source_label: str | None = None,
        tags: list[str] | None = None,
        confirmed_by: str = "operator",
        memory_id: WorkspaceMemoryId | None = None,
    ) -> WorkspaceMemoryEntry:
        self._ensure_session_exists(session_id)
        redacted_content, redacted = redact_sensitive_text(content)
        redacted_summary = None
        if summary is not None:
            redacted_summary, summary_redacted = redact_sensitive_text(summary)
            redacted = redacted or summary_redacted
        resolved_memory_id = memory_id or new_workspace_memory_id()
        provenance = WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.OPERATOR,
            source_label=source_label or "operator note",
        )
        self._repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryCreated(
                        memory_id=resolved_memory_id,
                        kind=kind,
                        content=redacted_content,
                        summary=redacted_summary,
                        provenance=provenance,
                        created_by=confirmed_by,
                        tags=tags or [],
                        redacted=redacted,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryConfirmed(
                        memory_id=resolved_memory_id,
                        confirmed_by=confirmed_by,
                        reason="operator-confirmed memory capture",
                    ),
                ),
            ]
        )
        entry = self._repository.get_workspace_memory(resolved_memory_id)
        if entry is None:
            raise ValueError(
                f"workspace memory was not projected: {resolved_memory_id}"
            )
        return entry

    def _require_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
    ) -> WorkspaceMemoryCandidate:
        for candidate in self.list_candidates(session_id):
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"unknown workspace memory candidate: {candidate_id}")

    def _runtime_note_candidates(
        self,
        session_id: SessionId,
    ) -> list[WorkspaceMemoryCandidate]:
        candidates: list[WorkspaceMemoryCandidate] = []
        for note in self._repository.list_runtime_notes(
            session_id,
            include_inherited=False,
        ):
            content, redacted = redact_sensitive_text(note.message)
            kind = _kind_for_runtime_note(note)
            summary = _summarize(content)
            provenance = WorkspaceMemoryProvenance(
                source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                session_id=session_id,
                source_sequence=note.source_sequence,
                source_label=f"runtime_note:{note.category}",
            )
            candidates.append(
                _candidate(
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

    def _task_outcome_candidates(
        self,
        session_id: SessionId,
    ) -> list[WorkspaceMemoryCandidate]:
        candidates: list[WorkspaceMemoryCandidate] = []
        for task in self._repository.list_tasks(session_id=session_id):
            if task.status not in _TASK_OUTCOME_STATUSES:
                continue
            detail = (
                f" Task detail: {task.blocked_detail}" if task.blocked_detail else ""
            )
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
                _candidate(
                    session_id=session_id,
                    kind=WorkspaceMemoryKind.TASK_OUTCOME,
                    content=content,
                    summary=_summarize(content),
                    provenance=provenance,
                    tags=["task", task.status.value],
                    redacted=redacted,
                    source_label=f"task {task.task_id}",
                    created_at=task.updated_at,
                )
            )
        return candidates

    def _stable_command_candidates(
        self,
        session_id: SessionId,
    ) -> list[WorkspaceMemoryCandidate]:
        events = self._repository.read_session_events(session_id)
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
                _candidate(
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

    def _repeated_failure_candidates(
        self,
        session_id: SessionId,
    ) -> list[WorkspaceMemoryCandidate]:
        buckets: dict[str, list[tuple[EventEnvelope, ToolExecutionCompleted]]] = {}
        for event in self._repository.read_session_events(session_id):
            payload = event.payload
            if isinstance(payload, ToolExecutionCompleted) and not payload.success:
                key = _summarize(payload.summary).casefold()
                buckets.setdefault(key, []).append((event, payload))
        candidates: list[WorkspaceMemoryCandidate] = []
        for failures in buckets.values():
            if len(failures) < 2:
                continue
            event, payload = failures[-1]
            content, redacted = redact_sensitive_text(
                f"Repeated tool failure observed {len(failures)} times: "
                f"{payload.summary}"
            )
            candidates.append(
                _candidate(
                    session_id=session_id,
                    kind=WorkspaceMemoryKind.FAILURE_PATTERN,
                    content=content,
                    summary=f"Repeated failure: {_summarize(payload.summary)}",
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

    def _confirmed_fix_candidates(
        self,
        session_id: SessionId,
    ) -> list[WorkspaceMemoryCandidate]:
        events = self._repository.read_session_events(session_id)
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
                _candidate(
                    session_id=session_id,
                    kind=WorkspaceMemoryKind.FACT,
                    content=content,
                    summary=f"Approved fix completed: {_summarize(approval.subject)}",
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

    def _model_assisted_candidates(
        self,
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
                _candidate(
                    session_id=session_id,
                    kind=suggestion.kind,
                    content=content,
                    summary=summary or _summarize(content),
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

    def _excluded_candidate_ids(self, session_id: SessionId) -> set[str]:
        excluded_ids: set[str] = set()
        for event in self._repository.read_session_events(session_id):
            payload = event.payload
            if isinstance(payload, WorkspaceMemoryCandidateRejected):
                excluded_ids.add(payload.candidate_id)
            elif isinstance(payload, WorkspaceMemoryConfirmed):
                prefix = "confirmed candidate "
                if payload.reason is not None and payload.reason.startswith(prefix):
                    excluded_ids.add(payload.reason.removeprefix(prefix))
        return excluded_ids

    def _ensure_session_exists(self, session_id: SessionId) -> None:
        if self._repository.get_session(session_id) is None:
            raise ValueError(f"unknown session_id: {session_id}")


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
_SUPPRESSED_NOTE_CATEGORIES = {"debug", "scratch", "transient"}


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


def _candidate_is_useful(candidate: WorkspaceMemoryCandidate) -> bool:
    content = " ".join(candidate.content.split())
    if len(content) < 16:
        return False
    if candidate.provenance.source_label is not None:
        label = candidate.provenance.source_label.casefold()
        if any(category in label for category in _SUPPRESSED_NOTE_CATEGORIES):
            return False
    return True


def _dedupe_candidates(
    candidates: Sequence[WorkspaceMemoryCandidate],
) -> list[WorkspaceMemoryCandidate]:
    seen: set[tuple[str, str]] = set()
    deduped: list[WorkspaceMemoryCandidate] = []
    for candidate in candidates:
        key = (candidate.kind.value, " ".join(candidate.content.casefold().split()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _filter_stale_candidates(
    candidates: Sequence[WorkspaceMemoryCandidate],
    *,
    now: datetime,
    max_age: timedelta,
) -> list[WorkspaceMemoryCandidate]:
    fresh: list[WorkspaceMemoryCandidate] = []
    for candidate in candidates:
        if candidate.created_at is not None and now - candidate.created_at > max_age:
            continue
        fresh.append(candidate)
    return fresh


def _merge_text(existing: str, candidate: str) -> str:
    if candidate.casefold() in existing.casefold():
        return existing
    return f"{existing.rstrip()}\n\n{candidate.strip()}"


def redact_sensitive_text(value: str) -> tuple[str, bool]:
    """Redact obvious secrets from operator-reviewed memory text."""

    redacted = False

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal redacted
        redacted = True
        return f"{match.group(1)}=<redacted>"

    value = _SENSITIVE_ASSIGNMENT.sub(replace_assignment, value)

    def replace_token(match: re.Match[str]) -> str:
        nonlocal redacted
        redacted = True
        return "<redacted-token>"

    value = _LONG_SECRETISH_TOKEN.sub(replace_token, value)
    return value, redacted


def _kind_for_runtime_note(note: RuntimeNoteRecord) -> WorkspaceMemoryKind:
    if note.category.lower() in {"operator", "preference", "user"}:
        return WorkspaceMemoryKind.USER_PREFERENCE
    return WorkspaceMemoryKind.FACT


def _candidate(
    *,
    session_id: SessionId,
    kind: WorkspaceMemoryKind,
    content: str,
    summary: str | None,
    provenance: WorkspaceMemoryProvenance,
    tags: list[str],
    redacted: bool,
    source_label: str,
    created_at: datetime | None,
) -> WorkspaceMemoryCandidate:
    candidate_id = _candidate_id(kind, content, provenance)
    return WorkspaceMemoryCandidate(
        candidate_id=candidate_id,
        session_id=session_id,
        kind=kind,
        content=content,
        summary=summary,
        provenance=provenance,
        tags=list(dict.fromkeys(tags)),
        redacted=redacted,
        source_label=source_label,
        created_at=created_at,
    )


def _candidate_id(
    kind: WorkspaceMemoryKind,
    content: str,
    provenance: WorkspaceMemoryProvenance,
) -> str:
    payload = {
        "kind": kind.value,
        "content": content,
        "provenance": provenance.model_dump(mode="json", exclude_none=True),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return digest[:24]


def _summarize(content: str) -> str:
    normalized = " ".join(content.split())
    return normalized[:497] + "..." if len(normalized) > 500 else normalized


__all__ = [
    "MemoryExtractionPolicy",
    "ModelMemorySuggestion",
    "WorkspaceMemoryCandidate",
    "WorkspaceMemoryCaptureService",
    "redact_sensitive_text",
]
