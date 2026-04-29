"""Commit-event construction for review-gated workspace memory capture."""

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryCandidateRejected
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryCreated
from glassbox.core.events import WorkspaceMemoryUpdated
from glassbox.core.ids import SessionId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.ids import new_workspace_memory_id
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType
from glassbox.runtime.workspace_memory_candidates import WorkspaceMemoryCandidate
from glassbox.runtime.workspace_memory_redaction import redact_sensitive_text


def build_confirm_candidate_events(
    session_id: SessionId,
    candidate: WorkspaceMemoryCandidate,
    *,
    confirmed_by: str,
    memory_id: WorkspaceMemoryId | None = None,
    kind: WorkspaceMemoryKind | None = None,
    content: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> tuple[WorkspaceMemoryId, list[EventEnvelope]]:
    resolved_memory_id = memory_id or new_workspace_memory_id()
    resolved_content, content_redacted = redact_sensitive_text(
        content or candidate.content
    )
    resolved_summary = summary if summary is not None else candidate.summary
    summary_redacted = False
    if resolved_summary is not None:
        resolved_summary, summary_redacted = redact_sensitive_text(resolved_summary)
    return resolved_memory_id, [
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
                redacted=candidate.redacted or content_redacted or summary_redacted,
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


def build_merge_candidate_events(
    session_id: SessionId,
    candidate: WorkspaceMemoryCandidate,
    existing: WorkspaceMemoryEntry,
    *,
    memory_id: WorkspaceMemoryId,
    merged_by: str,
) -> list[EventEnvelope]:
    return [
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


def build_reject_candidate_event(
    session_id: SessionId,
    candidate: WorkspaceMemoryCandidate,
    *,
    rejected_by: str,
    reason: str,
) -> EventEnvelope:
    return EventEnvelope(
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


def build_operator_memory_events(
    session_id: SessionId,
    *,
    kind: WorkspaceMemoryKind,
    content: str,
    summary: str | None,
    source_label: str | None,
    tags: list[str] | None,
    confirmed_by: str,
    memory_id: WorkspaceMemoryId | None,
) -> tuple[WorkspaceMemoryId, list[EventEnvelope]]:
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
    return resolved_memory_id, [
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


def _merge_text(existing: str, candidate: str) -> str:
    if candidate.casefold() in existing.casefold():
        return existing
    return f"{existing.rstrip()}\n\n{candidate.strip()}"


__all__ = [
    "build_confirm_candidate_events",
    "build_merge_candidate_events",
    "build_operator_memory_events",
    "build_reject_candidate_event",
]
