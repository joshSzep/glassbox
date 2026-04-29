"""Operator-reviewed workspace memory capture helpers."""

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryCandidateRejected
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryCreated
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


class WorkspaceMemoryCaptureService:
    """Generate and commit operator-confirmed workspace memory."""

    def __init__(self, repository: WorkspaceMemoryCaptureRepository) -> None:
        self._repository = repository

    def list_candidates(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
    ) -> list[WorkspaceMemoryCandidate]:
        self._ensure_session_exists(session_id)
        excluded_ids = self._excluded_candidate_ids(session_id)
        candidates = [
            candidate
            for candidate in [
                *self._runtime_note_candidates(session_id),
                *self._task_outcome_candidates(session_id),
            ]
            if candidate.candidate_id not in excluded_ids
        ]
        return candidates if limit is None else candidates[:limit]

    def confirm_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        *,
        confirmed_by: str = "operator",
        memory_id: WorkspaceMemoryId | None = None,
    ) -> WorkspaceMemoryEntry:
        candidate = self._require_candidate(session_id, candidate_id)
        resolved_memory_id = memory_id or new_workspace_memory_id()
        self._repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryCreated(
                        memory_id=resolved_memory_id,
                        kind=candidate.kind,
                        content=candidate.content,
                        summary=candidate.summary,
                        provenance=candidate.provenance,
                        created_by=confirmed_by,
                        tags=candidate.tags,
                        redacted=candidate.redacted,
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
    "WorkspaceMemoryCandidate",
    "WorkspaceMemoryCaptureService",
    "redact_sensitive_text",
]
