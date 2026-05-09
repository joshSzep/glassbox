"""Typed context assembly facade for model turns."""

from collections.abc import Sequence

from glassbox.core.ids import SessionId
from glassbox.runtime.context_formatting import format_checkpoint_resume_for_prompt
from glassbox.runtime.context_formatting import format_context_compactions_for_prompt
from glassbox.runtime.context_formatting import format_repository_context_for_prompt
from glassbox.runtime.context_formatting import format_repository_index_for_prompt
from glassbox.runtime.context_formatting import (
    format_repository_intelligence_for_prompt,
)
from glassbox.runtime.context_formatting import format_runtime_notes_for_prompt
from glassbox.runtime.context_formatting import format_tool_schemas_for_prompt
from glassbox.runtime.context_formatting import format_transcript_for_prompt
from glassbox.runtime.context_formatting import format_workspace_memory_for_prompt
from glassbox.runtime.context_formatting import normalize_tool_schemas
from glassbox.runtime.context_models import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_models import ArtifactBackedContextSnapshot
from glassbox.runtime.context_models import ArtifactBackedContextSummarySnapshot
from glassbox.runtime.context_models import CheckpointResumeSnapshot
from glassbox.runtime.context_models import ContextCompactionContextItemSnapshot
from glassbox.runtime.context_models import ContextCompactionContextSnapshot
from glassbox.runtime.context_models import ContextCompactionFreshnessCueSnapshot
from glassbox.runtime.context_models import PolicyContext
from glassbox.runtime.context_models import PytestFailureDigestArtifact
from glassbox.runtime.context_models import RepositoryContextSnapshot
from glassbox.runtime.context_models import RepositoryIndexContextItemSnapshot
from glassbox.runtime.context_models import RepositoryIndexContextSnapshot
from glassbox.runtime.context_models import RepositoryIntelligenceContextItemSnapshot
from glassbox.runtime.context_models import RepositoryIntelligenceContextSnapshot
from glassbox.runtime.context_models import RepositoryIntelligenceContextSourceSnapshot
from glassbox.runtime.context_models import RuntimeContextNoteSnapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_models import TurnContext
from glassbox.runtime.context_models import WorkingSetItemSnapshot
from glassbox.runtime.context_models import WorkingSetSnapshot
from glassbox.runtime.context_models import WorkspaceMemoryContextItemSnapshot
from glassbox.runtime.context_models import WorkspaceMemoryContextProvenanceSnapshot
from glassbox.runtime.context_snapshots import build_artifact_backed_context_snapshot
from glassbox.runtime.context_snapshots import build_pytest_failure_digest_artifact
from glassbox.runtime.context_snapshots import build_repository_context_snapshot
from glassbox.runtime.context_snapshots import build_repository_index_context_snapshot
from glassbox.runtime.context_snapshots import build_runtime_context_snapshot
from glassbox.runtime.context_snapshots import build_workspace_memory_context_snapshot
from glassbox.runtime.context_working_set import build_working_set_snapshot
from glassbox.services import SessionRepository
from glassbox.tools import ToolRegistry
from glassbox.tools import ToolSchema


class TurnContextBuilder:
    """Build a stable typed turn context from persisted session data."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def build(
        self,
        session_id: SessionId,
        *,
        tool_schemas: Sequence[ToolSchema] = (),
        tool_registry: ToolRegistry | None = None,
        repo_context: str | None = None,
        memory_notes: Sequence[str] = (),
        working_set: WorkingSetSnapshot | None = None,
        artifact_context: ArtifactBackedContextSnapshot | None = None,
        workspace_memory: Sequence[WorkspaceMemoryContextItemSnapshot] = (),
        repository_index: RepositoryIndexContextSnapshot | None = None,
        repository_intelligence: RepositoryIntelligenceContextSnapshot | None = None,
        checkpoint_context: CheckpointResumeSnapshot | None = None,
        context_compactions: ContextCompactionContextSnapshot | None = None,
    ) -> TurnContext:
        session = self._session_repository.get_session(session_id)
        session_state = self._session_repository.get_session_state(session_id)
        if session is None or session_state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        if tool_registry is not None and tool_schemas:
            raise ValueError("pass either tool_registry or tool_schemas, not both")

        transcript = sorted(
            self._session_repository.list_transcript_messages(session_id),
            key=lambda message: message.created_at,
        )
        normalized_tools = (
            tool_registry.list_schemas()
            if tool_registry is not None
            else normalize_tool_schemas(tool_schemas)
        )
        return TurnContext(
            session_id=session_id,
            session_status=session_state.status,
            current_turn_id=session_state.current_turn_id,
            last_sequence=session_state.last_sequence,
            transcript=transcript,
            available_tools=normalized_tools,
            policy=PolicyContext(
                approval_mode=session.approval_mode,
                pending_approval_id=session_state.pending_approval_id,
            ),
            repo_context=repo_context,
            memory_notes=list(memory_notes),
            working_set=working_set,
            artifact_context=artifact_context,
            workspace_memory=list(workspace_memory),
            repository_index=repository_index,
            repository_intelligence=repository_intelligence,
            checkpoint_context=checkpoint_context,
            context_compactions=context_compactions,
        )

    def build_from_runtime_context(
        self,
        session_id: SessionId,
        runtime_context: RuntimeContextSnapshot,
        *,
        tool_schemas: Sequence[ToolSchema] = (),
        tool_registry: ToolRegistry | None = None,
    ) -> TurnContext:
        """Build a turn context from a shared structured runtime-context snapshot."""

        repository_context = format_repository_context_for_prompt(
            runtime_context.repository_context
        )
        turn_repository_index = (
            runtime_context.repository_index
            if runtime_context.repository_index is not None
            and runtime_context.repository_index.status == "fresh"
            else None
        )
        turn_repository_intelligence = (
            runtime_context.repository_intelligence
            if runtime_context.repository_intelligence is not None
            and runtime_context.repository_intelligence.status != "missing"
            else None
        )
        repository_index_context = format_repository_index_for_prompt(
            turn_repository_index
        )
        if repository_index_context:
            repository_context = f"{repository_context}\n\n{repository_index_context}"

        return self.build(
            session_id,
            tool_schemas=tool_schemas,
            tool_registry=tool_registry,
            repo_context=repository_context,
            memory_notes=[
                *format_runtime_notes_for_prompt(runtime_context.runtime_notes),
                *format_workspace_memory_for_prompt(runtime_context.workspace_memory),
                *(
                    format_checkpoint_resume_for_prompt(
                        runtime_context.checkpoint_resume
                    )
                    if runtime_context.checkpoint_resume is not None
                    else []
                ),
                *format_context_compactions_for_prompt(
                    runtime_context.context_compactions
                ),
            ],
            working_set=runtime_context.working_set,
            artifact_context=runtime_context.artifact_context,
            workspace_memory=runtime_context.workspace_memory,
            repository_index=turn_repository_index,
            repository_intelligence=turn_repository_intelligence,
            checkpoint_context=runtime_context.checkpoint_resume,
            context_compactions=runtime_context.context_compactions,
        )


__all__ = [
    "ArtifactBackedContextSnapshot",
    "ArtifactBackedContextSummarySnapshot",
    "CheckpointResumeSnapshot",
    "ContextCompactionContextItemSnapshot",
    "ContextCompactionContextSnapshot",
    "ContextCompactionFreshnessCueSnapshot",
    "build_artifact_backed_context_snapshot",
    "build_pytest_failure_digest_artifact",
    "build_repository_context_snapshot",
    "build_repository_index_context_snapshot",
    "build_runtime_context_snapshot",
    "build_workspace_memory_context_snapshot",
    "build_working_set_snapshot",
    "format_repository_index_for_prompt",
    "format_repository_intelligence_for_prompt",
    "format_repository_context_for_prompt",
    "format_runtime_notes_for_prompt",
    "format_checkpoint_resume_for_prompt",
    "format_context_compactions_for_prompt",
    "format_tool_schemas_for_prompt",
    "format_transcript_for_prompt",
    "format_workspace_memory_for_prompt",
    "normalize_tool_schemas",
    "PolicyContext",
    "PYTEST_FAILURE_DIGEST_ARTIFACT_KIND",
    "PytestFailureDigestArtifact",
    "RepositoryIndexContextItemSnapshot",
    "RepositoryIndexContextSnapshot",
    "RepositoryIntelligenceContextItemSnapshot",
    "RepositoryIntelligenceContextSnapshot",
    "RepositoryIntelligenceContextSourceSnapshot",
    "RepositoryContextSnapshot",
    "RuntimeContextNoteSnapshot",
    "RuntimeContextSnapshot",
    "ToolSchema",
    "TurnContext",
    "TurnContextBuilder",
    "WorkspaceMemoryContextItemSnapshot",
    "WorkspaceMemoryContextProvenanceSnapshot",
    "WorkingSetItemSnapshot",
    "WorkingSetSnapshot",
]
