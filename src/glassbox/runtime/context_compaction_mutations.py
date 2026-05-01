"""Mutation operations for deterministic context compactions."""

from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import ContextCompactionFreshnessChanged
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_context_compaction_id
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.runtime.context_compaction_artifact import (
    build_context_compaction_artifact,
)
from glassbox.runtime.context_compaction_freshness import (
    latest_material_source_sequence,
)
from glassbox.runtime.context_compaction_range import (
    validate_source_range_within_reference_cap,
)
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def create_deterministic_context_compaction(
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    *,
    scope: ContextCompactionScope = ContextCompactionScope.TRANSCRIPT,
    task_id: TaskId | None = None,
    source_start_sequence: int | None = None,
    source_end_sequence: int | None = None,
) -> ContextCompactionCreated:
    """Create a local deterministic compaction artifact and canonical event."""

    session = session_repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    events = session_repository.read_session_events(session_id)
    if not events:
        raise ValueError(f"session {session_id} has no events to compact")

    start = (
        source_start_sequence
        if source_start_sequence is not None
        else events[0].sequence
    )
    end = (
        source_end_sequence if source_end_sequence is not None else events[-1].sequence
    )
    if end < start:
        raise ValueError("source end sequence must be greater than or equal to start")
    source_events = [event for event in events if start <= event.sequence <= end]
    if not source_events:
        raise ValueError("selected source range contains no events")
    validate_source_range_within_reference_cap(
        source_events,
        source_start_sequence=start,
        source_end_sequence=end,
    )

    compaction_id = new_context_compaction_id()
    artifact = build_context_compaction_artifact(
        session_id,
        compaction_id=compaction_id,
        scope=scope,
        task_id=task_id,
        source_events=source_events,
        source_start_sequence=start,
        source_end_sequence=end,
    )
    stored_artifact = artifact_repository.write_text_artifact(
        session_id,
        artifact.model_dump_json(indent=2),
        suffix=".context-compaction.json",
    )
    payload = ContextCompactionCreated(
        compaction_id=compaction_id,
        scope=scope,
        source_start_sequence=start,
        source_end_sequence=end,
        summary=artifact.summary,
        artifact_id=stored_artifact.artifact_id,
        freshness=ContextCompactionFreshness.FRESH,
        task_id=task_id,
        source_artifact_ids=artifact.source_artifact_ids,
        decision_count=len(artifact.decisions),
        unresolved_question_count=len(artifact.unresolved_questions),
        accepted_risk_count=len(artifact.accepted_risks),
        limitations=artifact.limitations,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=payload)
    )
    return payload


def refresh_context_compaction(
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    compaction_id: ContextCompactionId,
    *,
    changed_by: str = "operator",
    reason: str | None = None,
) -> tuple[ContextCompactionCreated, ContextCompactionFreshnessChanged]:
    """Create a replacement compaction and mark the previous one superseded."""

    record = session_repository.get_context_compaction(session_id, compaction_id)
    if record is None:
        raise ValueError(f"unknown compaction_id: {compaction_id}")

    source_end_sequence = latest_material_source_sequence(
        session_repository.read_session_events(session_id),
        default=record.source_end_sequence,
    )
    refreshed = create_deterministic_context_compaction(
        session_repository,
        artifact_repository,
        session_id,
        scope=record.scope,
        task_id=record.task_id,
        source_start_sequence=record.source_start_sequence,
        source_end_sequence=source_end_sequence,
    )
    change = ContextCompactionFreshnessChanged(
        compaction_id=record.compaction_id,
        freshness=ContextCompactionFreshness.STALE,
        reason=reason
        or (
            "Compaction was refreshed; the replacement covers source events "
            f"{refreshed.source_start_sequence}-{refreshed.source_end_sequence}."
        ),
        changed_by=changed_by,
        superseded_by_compaction_id=refreshed.compaction_id,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=change)
    )
    return refreshed, change


def invalidate_context_compaction(
    session_repository: SessionRepository,
    session_id: SessionId,
    compaction_id: ContextCompactionId,
    *,
    reason: str,
    changed_by: str = "operator",
) -> ContextCompactionFreshnessChanged:
    """Record that a compaction must not be used for active context."""

    record = session_repository.get_context_compaction(session_id, compaction_id)
    if record is None:
        raise ValueError(f"unknown compaction_id: {compaction_id}")
    change = ContextCompactionFreshnessChanged(
        compaction_id=record.compaction_id,
        freshness=ContextCompactionFreshness.INVALIDATED,
        reason=reason,
        changed_by=changed_by,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=change)
    )
    return change


__all__ = [
    "create_deterministic_context_compaction",
    "invalidate_context_compaction",
    "refresh_context_compaction",
]
