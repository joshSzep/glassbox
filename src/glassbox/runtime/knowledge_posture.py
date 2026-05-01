"""Unified workspace knowledge freshness posture."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

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

_ACTIVE_SESSION_STATUSES = {
    SessionStatus.RUNNING.value,
    SessionStatus.AWAITING_USER_INPUT.value,
    SessionStatus.AWAITING_APPROVAL.value,
}


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
    active_session_without_checkpoint_count = 0
    compaction_count = 0
    stale_compaction_count = 0
    for session in sessions:
        checkpoints = session_repository.list_task_checkpoints(
            session.session_id,
            limit=None,
        )
        checkpoint_count += len(checkpoints)
        session_status = (
            session.status.value if hasattr(session.status, "value") else session.status
        )
        if session_status in _ACTIVE_SESSION_STATUSES and not checkpoints:
            active_session_without_checkpoint_count += 1
        compactions = session_repository.list_context_compactions(
            session.session_id,
            limit=None,
        )
        compaction_count += len(compactions)
        stale_compaction_count += sum(
            1
            for compaction in compactions
            if getattr(compaction.freshness, "value", compaction.freshness) != "fresh"
        )

    return build_knowledge_posture_from_sources(
        memory=build_workspace_memory_observability(session_repository),
        repository_index=build_repository_index_observability(workspace_root),
        checkpoint_count=checkpoint_count,
        active_session_without_checkpoint_count=active_session_without_checkpoint_count,
        compaction_count=compaction_count,
        stale_compaction_count=stale_compaction_count,
        verification=build_verification_observability(workspace_root),
        provider_canary=load_provider_canary_evidence(workspace_root),
    )


def build_knowledge_posture_from_sources(
    *,
    memory: WorkspaceMemoryObservability,
    repository_index: RepositoryIndexObservability,
    checkpoint_count: int,
    active_session_without_checkpoint_count: int,
    compaction_count: int,
    stale_compaction_count: int,
    verification: VerificationObservability,
    provider_canary: ProviderCanaryEvidenceSummary,
) -> WorkspaceKnowledgePosture:
    """Build the unified posture from already-derived local source summaries."""

    cues = [
        _memory_cue(memory),
        _repository_index_cue(repository_index),
        _checkpoint_cue(
            checkpoint_count=checkpoint_count,
            active_session_without_checkpoint_count=active_session_without_checkpoint_count,
        ),
        _compaction_cue(
            compaction_count=compaction_count,
            stale_compaction_count=stale_compaction_count,
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


def _memory_cue(memory: WorkspaceMemoryObservability) -> KnowledgePostureCue:
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
    )


def _checkpoint_cue(
    *,
    checkpoint_count: int,
    active_session_without_checkpoint_count: int,
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
    )


def _compaction_cue(
    *,
    compaction_count: int,
    stale_compaction_count: int,
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


__all__ = [
    "KnowledgePostureCue",
    "KnowledgePostureStatus",
    "WorkspaceKnowledgePosture",
    "build_knowledge_posture_from_sources",
    "build_workspace_knowledge_posture",
]
