"""Source collection for workspace knowledge posture."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import SessionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import SessionStatus
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.observability_repository_index import (
    build_repository_index_observability,
)
from glassbox.runtime.observability_verification import build_verification_observability
from glassbox.runtime.observability_workspace_memory import (
    build_workspace_memory_observability,
)
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceSummary
from glassbox.services import SessionRepository

_ACTIVE_SESSION_STATUSES = {
    SessionStatus.RUNNING.value,
    SessionStatus.AWAITING_USER_INPUT.value,
    SessionStatus.AWAITING_APPROVAL.value,
}


@dataclass(frozen=True)
class KnowledgePostureSources:
    """Already-derived local sources used to build knowledge posture cues."""

    memory: WorkspaceMemoryObservability
    memory_entries: list[WorkspaceMemoryEntry]
    repository_index: RepositoryIndexObservability
    checkpoint_count: int
    active_session_without_checkpoint_count: int
    active_sessions_without_checkpoints: list[SessionRecord]
    checkpoint_records: list[TaskCheckpointRecord]
    compaction_count: int
    stale_compaction_count: int
    compaction_records: list[ContextCompactionRecord]
    verification: VerificationObservability
    provider_canary: ProviderCanaryEvidenceSummary


def collect_workspace_knowledge_sources(
    workspace_root: Path,
    session_repository: SessionRepository,
) -> KnowledgePostureSources:
    """Read existing projections and retained artifacts for posture derivation."""

    sessions = session_repository.list_sessions(limit=None)
    checkpoints = _collect_checkpoints(session_repository, sessions)
    compactions = _collect_compactions(session_repository, sessions)
    return KnowledgePostureSources(
        memory=build_workspace_memory_observability(session_repository),
        memory_entries=session_repository.list_workspace_memory(
            include_pruned=True,
            limit=5,
        ),
        repository_index=build_repository_index_observability(workspace_root),
        checkpoint_count=len(checkpoints.records),
        active_session_without_checkpoint_count=len(
            checkpoints.active_sessions_without_records,
        ),
        active_sessions_without_checkpoints=checkpoints.active_sessions_without_records,
        checkpoint_records=checkpoints.records,
        compaction_count=len(compactions.records),
        stale_compaction_count=compactions.stale_count,
        compaction_records=compactions.records,
        verification=build_verification_observability(workspace_root),
        provider_canary=load_provider_canary_evidence(workspace_root),
    )


@dataclass(frozen=True)
class _CheckpointCollection:
    records: list[TaskCheckpointRecord]
    active_sessions_without_records: list[SessionRecord]


@dataclass(frozen=True)
class _CompactionCollection:
    records: list[ContextCompactionRecord]
    stale_count: int


def _collect_checkpoints(
    session_repository: SessionRepository,
    sessions: list[SessionRecord],
) -> _CheckpointCollection:
    records: list[TaskCheckpointRecord] = []
    active_sessions_without_records: list[SessionRecord] = []
    for session in sessions:
        checkpoints = session_repository.list_task_checkpoints(
            session.session_id,
            limit=None,
        )
        records.extend(checkpoints)
        session_status = (
            session.status.value if hasattr(session.status, "value") else session.status
        )
        if session_status in _ACTIVE_SESSION_STATUSES and not checkpoints:
            active_sessions_without_records.append(session)
    return _CheckpointCollection(
        records=records,
        active_sessions_without_records=active_sessions_without_records,
    )


def _collect_compactions(
    session_repository: SessionRepository,
    sessions: list[SessionRecord],
) -> _CompactionCollection:
    records: list[ContextCompactionRecord] = []
    stale_count = 0
    for session in sessions:
        compactions = session_repository.list_context_compactions(
            session.session_id,
            limit=None,
        )
        records.extend(compactions)
        stale_count += sum(
            1
            for compaction in compactions
            if getattr(compaction.freshness, "value", compaction.freshness) != "fresh"
        )
    return _CompactionCollection(records=records, stale_count=stale_count)


__all__ = [
    "KnowledgePostureSources",
    "collect_workspace_knowledge_sources",
]
