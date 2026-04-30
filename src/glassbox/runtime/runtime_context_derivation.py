"""Shared derivation of structured runtime-context snapshots."""

from pathlib import Path

from glassbox.core.ids import SessionId
from glassbox.runtime.checkpoints import build_checkpoint_resume_snapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_snapshots import build_artifact_backed_context_snapshot
from glassbox.runtime.context_snapshots import build_repository_index_context_snapshot
from glassbox.runtime.context_snapshots import build_runtime_context_snapshot
from glassbox.runtime.context_snapshots import build_workspace_memory_context_snapshot
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
        build_workspace_memory_context_snapshot(session_repository)
    )
    session_state = session_repository.get_session_state(session_id)
    latest_checkpoint = session_repository.get_latest_task_checkpoint(session_id)
    latest_session_sequence = (
        session_state.last_sequence
        if session_state is not None
        else (latest_checkpoint.last_sequence if latest_checkpoint is not None else 0)
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
        checkpoint_resume=build_checkpoint_resume_snapshot(
            latest_checkpoint,
            latest_session_sequence=latest_session_sequence,
            workspace_root=workspace_root,
        ),
    )
