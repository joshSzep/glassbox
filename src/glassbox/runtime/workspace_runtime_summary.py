"""Workspace runtime summary helpers shared by API and CLI callers."""

from pathlib import Path

from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.observability import build_background_job_observability
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView
from glassbox.services import SessionRepository


def build_workspace_runtime_summary(
    workspace_root: Path,
    owner_status: RuntimeOwnerStatus,
    session_repository: SessionRepository,
) -> WorkspaceRuntimeSummaryView:
    """Build the compact runtime summary used by aggregate queue consumers."""

    record = owner_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    background_jobs = build_background_job_observability(session_repository)
    return WorkspaceRuntimeSummaryView(
        workspace_root=str(workspace_root),
        state=owner_status.state,
        health=owner_status.health,
        pid=record.pid if record is not None else None,
        dashboard_url=dashboard_url,
        health_url=(dashboard_url.rstrip("/") + "/healthz") if dashboard_url else None,
        session_index_url=dashboard_url,
        started_at=record.started_at if record is not None else None,
        background_job_failed_count=background_jobs.failed_count,
        background_job_retryable_count=background_jobs.retryable_count,
        background_job_abandoned_count=background_jobs.abandoned_count,
    )


__all__ = ["build_workspace_runtime_summary"]
