"""Workspace-memory prompt-use evidence recording."""

from collections.abc import Sequence

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryUsedInContext
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.services import SessionRepository


def record_workspace_memory_context_use(
    session_repository: SessionRepository,
    session_id: SessionId,
    *,
    turn_id: TurnId,
    memory_ids: Sequence[WorkspaceMemoryId],
    prompt_section: str,
    reason: str,
) -> None:
    """Record memory IDs selected for prompt context without duplicating evidence."""

    existing = {
        (payload.memory_id, payload.turn_id, payload.prompt_section)
        for payload in (
            event.payload
            for event in session_repository.read_session_events(session_id)
        )
        if isinstance(payload, WorkspaceMemoryUsedInContext)
    }
    events = [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=WorkspaceMemoryUsedInContext(
                memory_id=memory_id,
                turn_id=turn_id,
                prompt_section=prompt_section,
                reason=reason,
            ),
        )
        for memory_id in memory_ids
        if (memory_id, turn_id, prompt_section) not in existing
    ]
    if events:
        session_repository.append_events(events)


__all__ = ["record_workspace_memory_context_use"]
