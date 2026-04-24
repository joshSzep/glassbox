"""Typed context assembly facade for model turns."""

from __future__ import annotations

from collections.abc import Sequence

from glassbox.core.ids import SessionId
from glassbox.runtime.context_formatting import format_repository_context_for_prompt
from glassbox.runtime.context_formatting import format_tool_schemas_for_prompt
from glassbox.runtime.context_formatting import format_transcript_for_prompt
from glassbox.runtime.context_formatting import normalize_tool_schemas
from glassbox.runtime.context_models import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_models import ArtifactBackedContextSnapshot
from glassbox.runtime.context_models import ArtifactBackedContextSummarySnapshot
from glassbox.runtime.context_models import PolicyContext
from glassbox.runtime.context_models import PytestFailureDigestArtifact
from glassbox.runtime.context_models import RepositoryContextSnapshot
from glassbox.runtime.context_models import RuntimeContextNoteSnapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_models import TurnContext
from glassbox.runtime.context_models import WorkingSetItemSnapshot
from glassbox.runtime.context_models import WorkingSetSnapshot
from glassbox.runtime.context_snapshots import build_artifact_backed_context_snapshot
from glassbox.runtime.context_snapshots import build_pytest_failure_digest_artifact
from glassbox.runtime.context_snapshots import build_repository_context_snapshot
from glassbox.runtime.context_snapshots import build_runtime_context_snapshot
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
        )


__all__ = [
    "ArtifactBackedContextSnapshot",
    "ArtifactBackedContextSummarySnapshot",
    "build_artifact_backed_context_snapshot",
    "build_pytest_failure_digest_artifact",
    "build_repository_context_snapshot",
    "build_runtime_context_snapshot",
    "build_working_set_snapshot",
    "format_repository_context_for_prompt",
    "format_tool_schemas_for_prompt",
    "format_transcript_for_prompt",
    "normalize_tool_schemas",
    "PolicyContext",
    "PYTEST_FAILURE_DIGEST_ARTIFACT_KIND",
    "PytestFailureDigestArtifact",
    "RepositoryContextSnapshot",
    "RuntimeContextNoteSnapshot",
    "RuntimeContextSnapshot",
    "ToolSchema",
    "TurnContext",
    "TurnContextBuilder",
    "WorkingSetItemSnapshot",
    "WorkingSetSnapshot",
]
