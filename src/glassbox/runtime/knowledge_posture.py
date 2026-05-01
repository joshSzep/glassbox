"""Unified workspace knowledge freshness posture."""

from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

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

type KnowledgePostureStatus = Literal[
    "fresh",
    "stale",
    "missing",
    "invalidated",
    "degraded",
    "advisory",
    "historical-only",
]
type KnowledgeCueSourceKind = Literal[
    "workspace-memory",
    "repository-index",
    "checkpoint",
    "context-compaction",
    "verification-summary",
    "provider-evidence",
    "session",
]

_ACTIVE_SESSION_STATUSES = {
    SessionStatus.RUNNING.value,
    SessionStatus.AWAITING_USER_INPUT.value,
    SessionStatus.AWAITING_APPROVAL.value,
}


class KnowledgeCueProvenance(BaseModel):
    """Bounded source reference behind one knowledge posture cue."""

    model_config = ConfigDict(extra="forbid")

    label: str
    source_kind: KnowledgeCueSourceKind
    source_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    artifact_id: str | None = None
    path: str | None = None
    source_start_sequence: int | None = Field(default=None, ge=0)
    source_end_sequence: int | None = Field(default=None, ge=0)
    last_sequence: int | None = Field(default=None, ge=0)
    timestamp: str | None = None
    freshness: str | None = None
    detail: str | None = None


class KnowledgePostureCue(BaseModel):
    """One derived freshness cue for a local knowledge source."""

    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    status: KnowledgePostureStatus
    summary: str
    authoritative_source: str
    inspect_commands: list[str] = Field(default_factory=list)
    source_count: int = Field(default=0, ge=0)
    provenance: list[KnowledgeCueProvenance] = Field(default_factory=list)


class WorkspaceKnowledgePosture(BaseModel):
    """Unified operator-facing knowledge posture."""

    model_config = ConfigDict(extra="forbid")

    overall_status: KnowledgePostureStatus
    cues: list[KnowledgePostureCue]
    next_actions: list[str] = Field(default_factory=list)


def build_workspace_knowledge_posture(
    workspace_root: Path,
    session_repository: SessionRepository,
) -> WorkspaceKnowledgePosture:
    """Derive knowledge posture from existing projections and artifacts."""

    sessions = session_repository.list_sessions(limit=None)
    checkpoint_count = 0
    active_sessions_without_checkpoints: list[SessionRecord] = []
    checkpoint_records: list[TaskCheckpointRecord] = []
    compaction_count = 0
    stale_compaction_count = 0
    compaction_records: list[ContextCompactionRecord] = []
    for session in sessions:
        checkpoints = session_repository.list_task_checkpoints(
            session.session_id,
            limit=None,
        )
        checkpoint_records.extend(checkpoints)
        checkpoint_count += len(checkpoints)
        session_status = (
            session.status.value if hasattr(session.status, "value") else session.status
        )
        if session_status in _ACTIVE_SESSION_STATUSES and not checkpoints:
            active_sessions_without_checkpoints.append(session)
        compactions = session_repository.list_context_compactions(
            session.session_id,
            limit=None,
        )
        compaction_records.extend(compactions)
        compaction_count += len(compactions)
        stale_compaction_count += sum(
            1
            for compaction in compactions
            if getattr(compaction.freshness, "value", compaction.freshness) != "fresh"
        )

    return build_knowledge_posture_from_sources(
        memory=build_workspace_memory_observability(session_repository),
        memory_entries=session_repository.list_workspace_memory(
            include_pruned=True,
            limit=5,
        ),
        repository_index=build_repository_index_observability(workspace_root),
        checkpoint_count=checkpoint_count,
        active_sessions_without_checkpoints=active_sessions_without_checkpoints,
        checkpoint_records=checkpoint_records,
        compaction_count=compaction_count,
        compaction_records=compaction_records,
        stale_compaction_count=stale_compaction_count,
        verification=build_verification_observability(workspace_root),
        provider_canary=load_provider_canary_evidence(workspace_root),
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

    active_session_count = active_session_without_checkpoint_count
    if active_session_count is None:
        active_session_count = len(active_sessions_without_checkpoints or [])
    cues = [
        _memory_cue(memory, memory_entries or []),
        _repository_index_cue(repository_index),
        _checkpoint_cue(
            checkpoint_count=checkpoint_count,
            active_session_without_checkpoint_count=active_session_count,
            active_sessions_without_checkpoints=active_sessions_without_checkpoints
            or [],
            checkpoint_records=checkpoint_records or [],
        ),
        _compaction_cue(
            compaction_count=compaction_count,
            stale_compaction_count=stale_compaction_count,
            compaction_records=compaction_records or [],
        ),
        _verification_cue(verification),
        _provider_cue(provider_canary),
    ]
    return WorkspaceKnowledgePosture(
        overall_status=_overall_status(cues),
        cues=cues,
        next_actions=_dedupe(
            command for cue in cues for command in cue.inspect_commands[:2]
        ),
    )


def _memory_cue(
    memory: WorkspaceMemoryObservability,
    memory_entries: list[WorkspaceMemoryEntry],
) -> KnowledgePostureCue:
    if memory.stale_count:
        status: KnowledgePostureStatus = "stale"
        summary = f"{memory.stale_count} stale memory entrie(s) need review."
    elif memory.invalidated_count and not memory.active_count:
        status = "invalidated"
        summary = "Only invalidated or inactive workspace memory is available."
    elif memory.active_count:
        status = "fresh"
        summary = f"{memory.active_count} active workspace memory entrie(s)."
    elif memory.imported_count:
        status = "historical-only"
        summary = f"{memory.imported_count} imported memory entrie(s)."
    else:
        status = "missing"
        summary = "No workspace memory has been confirmed."
    return KnowledgePostureCue(
        key="workspace-memory",
        title="Workspace Memory",
        status=status,
        summary=summary,
        authoritative_source="workspace_memory projection from canonical events",
        inspect_commands=["glassbox memory list --cwd .", *memory.next_actions],
        source_count=memory.active_count
        + memory.stale_count
        + memory.imported_count
        + memory.invalidated_count,
        provenance=[
            _memory_provenance(entry)
            for entry in _sort_latest(memory_entries, "updated_at")[:3]
        ],
    )


def _repository_index_cue(
    repository_index: RepositoryIndexObservability,
) -> KnowledgePostureCue:
    status_map: dict[str, KnowledgePostureStatus] = {
        "fresh": "fresh",
        "stale": "stale",
        "missing": "missing",
        "failed": "degraded",
    }
    status = status_map.get(repository_index.status, "degraded")
    return KnowledgePostureCue(
        key="repository-index",
        title="Repository Index",
        status=status,
        summary=(
            f"Repository index is {repository_index.status} with "
            f"{repository_index.entry_count} entrie(s)."
        ),
        authoritative_source="repository-index.json rebuildable artifact",
        inspect_commands=[
            "glassbox repo index status --cwd .",
            *repository_index.next_actions,
        ],
        source_count=repository_index.entry_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Repository index snapshot",
                source_kind="repository-index",
                source_id="repository-index",
                path=repository_index.path,
                timestamp=repository_index.built_at,
                freshness=repository_index.status,
                detail=repository_index.stale_reason
                or repository_index.failure_reason
                or repository_index.detail,
            )
        ],
    )


def _checkpoint_cue(
    *,
    checkpoint_count: int,
    active_session_without_checkpoint_count: int,
    active_sessions_without_checkpoints: list[SessionRecord],
    checkpoint_records: list[TaskCheckpointRecord],
) -> KnowledgePostureCue:
    if active_session_without_checkpoint_count:
        status: KnowledgePostureStatus = "degraded"
        summary = (
            f"{active_session_without_checkpoint_count} active session(s) lack "
            "checkpoint evidence."
        )
    elif checkpoint_count:
        status = "fresh"
        summary = f"{checkpoint_count} checkpoint record(s) are projected."
    else:
        status = "historical-only"
        summary = "No checkpoints are projected; this may be historical-only state."
    return KnowledgePostureCue(
        key="checkpoints",
        title="Checkpoints",
        status=status,
        summary=summary,
        authoritative_source=(
            "TaskCheckpointCreated events and task_checkpoints projection"
        ),
        inspect_commands=["glassbox session status SESSION_ID --cwd ."],
        source_count=checkpoint_count,
        provenance=[
            *[
                _checkpoint_provenance(checkpoint)
                for checkpoint in _sort_latest(checkpoint_records, "last_sequence")[:3]
            ],
            *[
                _session_without_checkpoint_provenance(session)
                for session in _sort_latest(
                    active_sessions_without_checkpoints,
                    "updated_at",
                )[:3]
            ],
        ][:5],
    )


def _compaction_cue(
    *,
    compaction_count: int,
    stale_compaction_count: int,
    compaction_records: list[ContextCompactionRecord],
) -> KnowledgePostureCue:
    if stale_compaction_count:
        status: KnowledgePostureStatus = "stale"
        summary = f"{stale_compaction_count} stale compaction artifact(s) need review."
    elif compaction_count:
        status = "fresh"
        summary = f"{compaction_count} fresh compaction artifact(s) are retained."
    else:
        status = "missing"
        summary = "No context compaction artifacts are retained."
    return KnowledgePostureCue(
        key="compactions",
        title="Context Compactions",
        status=status,
        summary=summary,
        authoritative_source=(
            "ContextCompactionCreated events, projection, and artifacts"
        ),
        inspect_commands=["glassbox session compactions SESSION_ID --cwd ."],
        source_count=compaction_count,
        provenance=[
            _compaction_provenance(compaction)
            for compaction in _sort_latest(compaction_records, "last_sequence")[:3]
        ],
    )


def _verification_cue(
    verification: VerificationObservability,
) -> KnowledgePostureCue:
    if not verification.summary_count:
        status: KnowledgePostureStatus = "missing"
        summary = "No retained eval or verification summary was found."
    elif verification.latest_suite_status == "passed":
        status = "fresh"
        summary = (
            f"Latest retained verification passed "
            f"({verification.latest_profile_id or 'unknown profile'})."
        )
    else:
        status = "degraded"
        summary = (
            f"Latest retained verification is "
            f"{verification.latest_suite_status or 'unknown'}."
        )
    return KnowledgePostureCue(
        key="verification",
        title="Verification Evidence",
        status=status,
        summary=summary,
        authoritative_source=".glassbox/evals retained summary artifacts",
        inspect_commands=["glassbox eval audit --cwd .", *verification.next_actions],
        source_count=verification.summary_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Latest retained verification summary",
                source_kind="verification-summary",
                source_id=verification.latest_profile_id,
                path=verification.latest_summary_path,
                freshness=verification.latest_suite_status,
                detail=(
                    f"exit_code={verification.latest_exit_code}; "
                    f"failed_cases={verification.latest_failed_case_count}"
                ),
            )
        ]
        if verification.latest_summary_path is not None
        else [],
    )


def _provider_cue(
    provider_canary: ProviderCanaryEvidenceSummary,
) -> KnowledgePostureCue:
    if provider_canary.freshness_status in {"fresh", "warning"}:
        status: KnowledgePostureStatus = "advisory"
    elif provider_canary.freshness_status in {"stale", "incompatible"}:
        status = "stale"
    elif provider_canary.freshness_status in {"failed"}:
        status = "degraded"
    else:
        status = "missing"
    return KnowledgePostureCue(
        key="provider-evidence",
        title="Provider Evidence",
        status=status,
        summary=(
            "Provider canary evidence is advisory: "
            f"{provider_canary.latest_status}; freshness "
            f"{provider_canary.freshness_status}."
        ),
        authoritative_source="retained provider-canary summary artifacts",
        inspect_commands=[
            "glassbox provider canary evidence --cwd .",
            *provider_canary.next_actions,
        ],
        source_count=provider_canary.summary_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Latest provider canary evidence",
                source_kind="provider-evidence",
                path=provider_canary.latest_summary_path,
                timestamp=provider_canary.latest_generated_at,
                freshness=provider_canary.freshness_status,
                detail=(
                    f"status={provider_canary.latest_status}; "
                    f"provider={provider_canary.provider or 'unknown'}; "
                    f"model={provider_canary.model_name or 'unknown'}"
                ),
            )
        ]
        if provider_canary.latest_summary_path is not None
        else [],
    )


def _memory_provenance(entry: WorkspaceMemoryEntry) -> KnowledgeCueProvenance:
    source_sequence = entry.provenance.source_sequence
    return KnowledgeCueProvenance(
        label=f"Memory {entry.memory_id}",
        source_kind="workspace-memory",
        source_id=str(entry.memory_id),
        session_id=str(entry.session_id),
        task_id=_optional_str(entry.provenance.task_id),
        artifact_id=_optional_str(entry.provenance.artifact_id),
        source_start_sequence=source_sequence,
        source_end_sequence=source_sequence,
        last_sequence=entry.last_sequence,
        timestamp=entry.updated_at.isoformat(),
        freshness=_enum_value(entry.state),
        detail=(
            f"{_enum_value(entry.provenance.source_type)}"
            f"{_detail_suffix(entry.provenance.source_label)}"
        ),
    )


def _checkpoint_provenance(
    checkpoint: TaskCheckpointRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label=f"Checkpoint {checkpoint.checkpoint_id}",
        source_kind="checkpoint",
        source_id=str(checkpoint.checkpoint_id),
        session_id=str(checkpoint.session_id),
        task_id=_optional_str(checkpoint.task_id),
        artifact_id=_optional_str(checkpoint.artifact_id),
        source_start_sequence=checkpoint.source_start_sequence,
        source_end_sequence=checkpoint.source_end_sequence,
        last_sequence=checkpoint.last_sequence,
        timestamp=checkpoint.created_at.isoformat(),
        freshness=checkpoint.verification_status or checkpoint.budget_status,
        detail=(
            checkpoint.current_phase.value
            if checkpoint.current_phase is not None
            else checkpoint.next_action
        ),
    )


def _session_without_checkpoint_provenance(
    session: SessionRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label="Active session without checkpoint",
        source_kind="session",
        source_id=str(session.session_id),
        session_id=str(session.session_id),
        source_start_sequence=0,
        source_end_sequence=session.last_sequence,
        last_sequence=session.last_sequence,
        timestamp=session.updated_at.isoformat(),
        freshness="missing-checkpoint",
        detail=f"{session.status.value} session has no checkpoint projection",
    )


def _compaction_provenance(
    compaction: ContextCompactionRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label=f"Compaction {compaction.compaction_id}",
        source_kind="context-compaction",
        source_id=str(compaction.compaction_id),
        session_id=str(compaction.session_id),
        task_id=_optional_str(compaction.task_id),
        artifact_id=str(compaction.artifact_id),
        source_start_sequence=compaction.source_start_sequence,
        source_end_sequence=compaction.source_end_sequence,
        last_sequence=compaction.last_sequence,
        timestamp=compaction.created_at.isoformat(),
        freshness=_enum_value(compaction.freshness),
        detail=compaction.freshness_reason or compaction.summary,
    )


def _overall_status(cues: list[KnowledgePostureCue]) -> KnowledgePostureStatus:
    statuses = {cue.status for cue in cues}
    for candidate in (
        "degraded",
        "stale",
        "invalidated",
        "missing",
        "advisory",
        "historical-only",
    ):
        if candidate in statuses:
            return candidate
    return "fresh"


def _dedupe(commands) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    return deduped


def _sort_latest(items: list[Any], attribute: str) -> list[Any]:
    return sorted(
        items,
        key=lambda item: _sort_key(getattr(item, attribute, None)),
        reverse=True,
    )


def _sort_key(value: Any) -> tuple[int, str]:
    if value is None:
        return (0, "")
    if hasattr(value, "isoformat"):
        return (1, value.isoformat())
    if isinstance(value, int):
        return (1, f"{value:020d}")
    return (1, str(value))


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _detail_suffix(value: str | None) -> str:
    return "" if value is None else f"; {value}"


__all__ = [
    "KnowledgeCueProvenance",
    "KnowledgeCueSourceKind",
    "KnowledgePostureCue",
    "KnowledgePostureStatus",
    "WorkspaceKnowledgePosture",
    "build_knowledge_posture_from_sources",
    "build_workspace_knowledge_posture",
]
