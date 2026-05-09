"""Shared derivation of structured runtime-context snapshots."""

from collections.abc import Sequence
from pathlib import Path

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryUsedInContext
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.runtime.checkpoints import build_checkpoint_resume_snapshot
from glassbox.runtime.context_compaction_service import (
    assessed_context_compaction_record,
)
from glassbox.runtime.context_models import ContextCompactionContextItemSnapshot
from glassbox.runtime.context_models import ContextCompactionContextSnapshot
from glassbox.runtime.context_models import ContextCompactionFreshnessCueSnapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_snapshots import build_artifact_backed_context_snapshot
from glassbox.runtime.context_snapshots import build_repository_index_context_snapshot
from glassbox.runtime.context_snapshots import (
    build_repository_intelligence_context_snapshot,
)
from glassbox.runtime.context_snapshots import build_runtime_context_snapshot
from glassbox.runtime.context_snapshots import build_workspace_memory_context_snapshot
from glassbox.runtime.context_snapshots import (
    repository_intelligence_context_memory_ids,
)
from glassbox.runtime.context_working_set import build_working_set_snapshot
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def derive_runtime_context_snapshot(
    session_repository: SessionRepository,
    session_id: SessionId,
    workspace_root: Path,
    *,
    artifact_repository: ArtifactRepository | None = None,
    include_stale_artifacts: bool = True,
) -> RuntimeContextSnapshot:
    """Return the shared structured runtime-context snapshot for one session."""

    artifact_context = None
    if artifact_repository is not None:
        artifact_context = build_artifact_backed_context_snapshot(
            session_repository,
            artifact_repository,
            session_id,
            include_stale=include_stale_artifacts,
        )

    workspace_memory, additional_workspace_memory_count, workspace_memory_bytes = (
        build_workspace_memory_context_snapshot(
            session_repository,
            workspace_root=workspace_root,
        )
    )
    session_state = session_repository.get_session_state(session_id)
    if session_state is not None and session_state.current_turn_id is not None:
        _record_workspace_memory_context_use(
            session_repository,
            session_id,
            turn_id=session_state.current_turn_id,
            memory_ids=[item.memory_id for item in workspace_memory],
            prompt_section="workspace_memory",
            reason=(
                "confirmed active memory included in runtime context; repository "
                "intelligence memory references remain separately inspectable"
            ),
        )
    latest_checkpoint = session_repository.get_latest_task_checkpoint(session_id)
    latest_session_sequence = (
        session_state.last_sequence
        if session_state is not None
        else (latest_checkpoint.last_sequence if latest_checkpoint is not None else 0)
    )
    repository_intelligence = build_repository_intelligence_context_snapshot(
        workspace_root
    )
    if session_state is not None and session_state.current_turn_id is not None:
        repository_intelligence_memory_ids = repository_intelligence_context_memory_ids(
            repository_intelligence
        )
        if repository_intelligence_memory_ids:
            _record_workspace_memory_context_use(
                session_repository,
                session_id,
                turn_id=session_state.current_turn_id,
                memory_ids=repository_intelligence_memory_ids,
                prompt_section="repository_intelligence",
                reason=(
                    "confirmed active memory-derived repository intelligence "
                    "included in bounded runtime context"
                ),
            )

    return build_runtime_context_snapshot(
        workspace_root,
        session_repository.list_runtime_notes(session_id),
        working_set=build_working_set_snapshot(session_repository, session_id),
        artifact_context=artifact_context,
        workspace_memory=workspace_memory,
        additional_workspace_memory_count=additional_workspace_memory_count,
        workspace_memory_context_bytes=workspace_memory_bytes,
        repository_index=build_repository_index_context_snapshot(workspace_root),
        repository_intelligence=repository_intelligence,
        checkpoint_resume=build_checkpoint_resume_snapshot(
            latest_checkpoint,
            latest_session_sequence=latest_session_sequence,
            workspace_root=workspace_root,
        ),
        context_compactions=build_context_compaction_context_snapshot(
            session_repository,
            session_id,
        ),
    )


def _record_workspace_memory_context_use(
    session_repository: SessionRepository,
    session_id: SessionId,
    *,
    turn_id: TurnId,
    memory_ids: Sequence[WorkspaceMemoryId],
    prompt_section: str,
    reason: str,
) -> None:
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


def build_context_compaction_context_snapshot(
    session_repository: SessionRepository,
    session_id: SessionId,
    *,
    item_limit: int = 3,
) -> ContextCompactionContextSnapshot:
    """Return fresh compactions that are safe to place in turn context."""

    rows = session_repository.list_context_compactions(
        session_id,
        limit=item_limit + 25,
    )
    events = session_repository.read_session_events(session_id)
    rows = [assessed_context_compaction_record(row, events) for row in rows]
    fresh_rows = [row for row in rows if row.freshness == "fresh"]
    stale_rows = [row for row in rows if row.freshness != "fresh"]
    selected = fresh_rows[:item_limit]
    stale_selected = stale_rows[:item_limit]
    return ContextCompactionContextSnapshot(
        items=[
            ContextCompactionContextItemSnapshot(
                compaction_id=row.compaction_id,
                scope=row.scope,
                artifact_id=row.artifact_id,
                source_start_sequence=row.source_start_sequence,
                source_end_sequence=row.source_end_sequence,
                summary=row.summary,
                freshness=row.freshness,
                limitations=row.limitations,
                decision_count=row.decision_count,
                unresolved_question_count=row.unresolved_question_count,
                accepted_risk_count=row.accepted_risk_count,
                freshness_reason=row.freshness_reason,
                superseded_by_compaction_id=row.superseded_by_compaction_id,
            )
            for row in selected
        ],
        stale_items=[
            ContextCompactionFreshnessCueSnapshot(
                compaction_id=row.compaction_id,
                scope=row.scope,
                artifact_id=row.artifact_id,
                source_start_sequence=row.source_start_sequence,
                source_end_sequence=row.source_end_sequence,
                freshness=row.freshness,
                reason=row.freshness_reason
                or "Compaction is not fresh enough for active prompt context.",
                superseded_by_compaction_id=row.superseded_by_compaction_id,
            )
            for row in stale_selected
        ],
        additional_item_count=max(len(fresh_rows) - len(selected), 0),
        stale_item_count=max(len(rows) - len(fresh_rows), 0),
    )
