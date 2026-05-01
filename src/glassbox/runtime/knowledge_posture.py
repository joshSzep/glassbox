"""Unified workspace knowledge freshness posture."""

from pathlib import Path

from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import SessionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.runtime.knowledge_posture_cues import build_knowledge_cues_from_sources
from glassbox.runtime.knowledge_posture_guidance import next_actions_from_cues
from glassbox.runtime.knowledge_posture_models import KnowledgeCueProvenance
from glassbox.runtime.knowledge_posture_models import KnowledgeCueSourceKind
from glassbox.runtime.knowledge_posture_models import KnowledgePostureCue
from glassbox.runtime.knowledge_posture_models import KnowledgePostureStatus
from glassbox.runtime.knowledge_posture_models import WorkspaceKnowledgePosture
from glassbox.runtime.knowledge_posture_ranking import overall_status
from glassbox.runtime.knowledge_posture_sources import KnowledgePostureSources
from glassbox.runtime.knowledge_posture_sources import (
    collect_workspace_knowledge_sources,
)
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceSummary
from glassbox.services import SessionRepository


def build_workspace_knowledge_posture(
    workspace_root: Path,
    session_repository: SessionRepository,
) -> WorkspaceKnowledgePosture:
    """Derive knowledge posture from existing projections and artifacts."""

    return _assemble_posture(
        collect_workspace_knowledge_sources(workspace_root, session_repository),
    )


def build_knowledge_posture_from_sources(
    *,
    memory: WorkspaceMemoryObservability,
    memory_entries: list[WorkspaceMemoryEntry] | None = None,
    repository_index: RepositoryIndexObservability,
    checkpoint_count: int,
    active_session_without_checkpoint_count: int | None = None,
    active_sessions_without_checkpoints: list[SessionRecord] | None = None,
    checkpoint_records: list[TaskCheckpointRecord] | None = None,
    compaction_count: int,
    stale_compaction_count: int,
    compaction_records: list[ContextCompactionRecord] | None = None,
    verification: VerificationObservability,
    provider_canary: ProviderCanaryEvidenceSummary,
) -> WorkspaceKnowledgePosture:
    """Build the unified posture from already-derived local source summaries."""

    active_sessions = active_sessions_without_checkpoints or []
    sources = KnowledgePostureSources(
        memory=memory,
        memory_entries=memory_entries or [],
        repository_index=repository_index,
        checkpoint_count=checkpoint_count,
        active_session_without_checkpoint_count=(
            active_session_without_checkpoint_count
            if active_session_without_checkpoint_count is not None
            else len(active_sessions)
        ),
        active_sessions_without_checkpoints=active_sessions,
        checkpoint_records=checkpoint_records or [],
        compaction_count=compaction_count,
        stale_compaction_count=stale_compaction_count,
        compaction_records=compaction_records or [],
        verification=verification,
        provider_canary=provider_canary,
    )
    return _assemble_posture(sources)


def _assemble_posture(
    sources: KnowledgePostureSources,
) -> WorkspaceKnowledgePosture:
    cues = build_knowledge_cues_from_sources(sources)
    return WorkspaceKnowledgePosture(
        overall_status=overall_status(cues),
        cues=cues,
        next_actions=next_actions_from_cues(cues),
    )


__all__ = [
    "KnowledgeCueProvenance",
    "KnowledgeCueSourceKind",
    "KnowledgePostureCue",
    "KnowledgePostureStatus",
    "WorkspaceKnowledgePosture",
    "build_knowledge_posture_from_sources",
    "build_workspace_knowledge_posture",
]
