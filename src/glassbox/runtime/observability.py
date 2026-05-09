"""Workspace observability report aggregation facade."""

from pathlib import Path

from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.observability_artifacts import build_artifact_observability
from glassbox.runtime.observability_background_jobs import (
    build_background_job_observability,
)
from glassbox.runtime.observability_branch_search import (
    build_branch_search_observability,
)
from glassbox.runtime.observability_models import ArtifactObservability
from glassbox.runtime.observability_models import BackgroundJobObservability
from glassbox.runtime.observability_models import BranchSearchObservability
from glassbox.runtime.observability_models import EventTransportObservability
from glassbox.runtime.observability_models import ProjectionObservability
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import RuntimeObservability
from glassbox.runtime.observability_models import TaskAutonomyObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.observability_models import WorkspaceObservabilityReport
from glassbox.runtime.observability_projections import build_projection_observability
from glassbox.runtime.observability_repository_index import (
    build_repository_index_observability,
)
from glassbox.runtime.observability_runtime import build_event_transport_observability
from glassbox.runtime.observability_runtime import build_runtime_observability
from glassbox.runtime.observability_task_autonomy import (
    build_task_autonomy_observability,
)
from glassbox.runtime.observability_verification import build_verification_observability
from glassbox.runtime.observability_workspace_memory import (
    build_workspace_memory_observability,
)
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.transport import RuntimeEventTransportStats
from glassbox.services import SessionRepository


def build_workspace_observability_report(
    *,
    workspace_root: Path,
    runtime_status: RuntimeOwnerStatus,
    session_repository: SessionRepository,
    event_transport_stats: RuntimeEventTransportStats,
) -> WorkspaceObservabilityReport:
    """Build one structured observability report for a workspace."""

    runtime = build_runtime_observability(
        runtime_status,
        event_transport_stats=event_transport_stats,
        workspace_root=workspace_root,
    )
    projections = build_projection_observability(session_repository)
    tasks = build_task_autonomy_observability(session_repository)
    background_jobs = build_background_job_observability(session_repository)
    memory = build_workspace_memory_observability(
        session_repository,
        workspace_root=workspace_root,
    )
    repository_index = build_repository_index_observability(workspace_root)
    branch_searches = build_branch_search_observability(session_repository)
    artifacts = build_artifact_observability(workspace_root, session_repository)
    verification = build_verification_observability(workspace_root)
    provider_canary = load_provider_canary_evidence(workspace_root)
    next_actions = [
        action
        for section in (
            runtime,
            projections,
            tasks,
            background_jobs,
            memory,
            repository_index,
            branch_searches,
            artifacts,
            verification,
            provider_canary,
        )
        for action in section.next_actions
    ]
    return WorkspaceObservabilityReport(
        workspace_root=str(workspace_root),
        runtime=runtime,
        projections=projections,
        tasks=tasks,
        background_jobs=background_jobs,
        memory=memory,
        repository_index=repository_index,
        branch_searches=branch_searches,
        artifacts=artifacts,
        verification=verification,
        provider_canary=provider_canary,
        next_actions=next_actions,
    )


__all__ = [
    "ArtifactObservability",
    "BackgroundJobObservability",
    "BranchSearchObservability",
    "EventTransportObservability",
    "ProjectionObservability",
    "RepositoryIndexObservability",
    "RuntimeObservability",
    "TaskAutonomyObservability",
    "VerificationObservability",
    "WorkspaceMemoryObservability",
    "WorkspaceObservabilityReport",
    "build_artifact_observability",
    "build_background_job_observability",
    "build_branch_search_observability",
    "build_event_transport_observability",
    "build_projection_observability",
    "build_repository_index_observability",
    "build_runtime_observability",
    "build_task_autonomy_observability",
    "build_verification_observability",
    "build_workspace_memory_observability",
    "build_workspace_observability_report",
]
