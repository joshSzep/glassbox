"""Read-only background job handlers."""

from pathlib import Path
from typing import cast
from uuid import UUID

from glassbox.core.models import BackgroundJobRecord
from glassbox.runtime.background_job_records import record_background_job_progress
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
from glassbox.store.artifact_retention import inspect_artifact_state


def run_read_only_background_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    *,
    worker_id: str,
) -> None:
    """Run a read-only or rebuildable maintenance background job."""

    del worker_id
    workspace_root = runtime_context.infrastructure.artifacts_root
    if job.job_type == "projection-health-refresh":
        _run_projection_health_refresh(runtime_context, job)
        return
    if job.job_type == "artifact-pressure-scan":
        _run_artifact_pressure_scan(runtime_context, workspace_root, job)
        return
    if job.job_type == "provider-evidence-freshness-scan":
        _run_provider_evidence_scan(runtime_context, workspace_root, job)
        return
    if job.job_type == "repository-index-refresh":
        _run_repository_index_refresh(runtime_context, workspace_root, job)
        return
    if job.job_type == "workspace-memory-candidate-scan":
        _run_workspace_memory_candidate_scan(runtime_context, job)
        return
    raise ValueError(f"unsupported read-only background job type: {job.job_type}")


def _run_projection_health_refresh(
    runtime_context: RuntimeContext, job: BackgroundJobRecord
) -> None:
    repository = runtime_context.repositories.sessions
    sessions = repository.list_sessions()
    degraded_count = 0
    for session in sessions:
        health = repository.inspect_session_projection_health(session.session_id)
        if health.degraded:
            degraded_count += 1
    record_background_job_progress(
        runtime_context,
        job,
        f"inspected projection health for {len(sessions)} session(s)",
    )
    repository.complete_background_job(
        job.job_id,
        summary=(
            f"Projection health refresh inspected {len(sessions)} session(s); "
            f"{degraded_count} degraded."
        ),
    )


def _run_artifact_pressure_scan(
    runtime_context: RuntimeContext,
    workspace_root: Path,
    job: BackgroundJobRecord,
) -> None:
    repository = runtime_context.repositories.sessions
    report = inspect_artifact_state(workspace_root, repository)
    record_background_job_progress(
        runtime_context,
        job,
        f"identified {len(report.candidates)} artifact prune candidate(s)",
    )
    repository.complete_background_job(
        job.job_id,
        summary=(
            f"Artifact pressure scan found {len(report.candidates)} candidate(s), "
            f"{len(report.missing_references)} missing reference(s), and "
            f"{report.candidate_size_bytes} reclaimable byte(s)."
        ),
    )


def _run_provider_evidence_scan(
    runtime_context: RuntimeContext,
    workspace_root: Path,
    job: BackgroundJobRecord,
) -> None:
    evidence = load_provider_canary_evidence(workspace_root)
    record_background_job_progress(
        runtime_context,
        job,
        f"loaded {evidence.summary_count} provider canary summary/summaries",
    )
    runtime_context.repositories.sessions.complete_background_job(
        job.job_id,
        summary=(
            f"Provider evidence freshness scan latest status: {evidence.latest_status}."
        ),
    )


def _run_repository_index_refresh(
    runtime_context: RuntimeContext,
    workspace_root: Path,
    job: BackgroundJobRecord,
) -> None:
    snapshot = build_and_write_repository_index(workspace_root)
    index_path = repository_index_path(workspace_root)
    record_background_job_progress(
        runtime_context,
        job,
        f"repository index refreshed {len(snapshot.entries)} entries",
    )
    runtime_context.repositories.sessions.complete_background_job(
        job.job_id,
        summary=(
            f"Repository index refresh wrote {len(snapshot.entries)} entries "
            f"to {index_path}."
        ),
    )


def _run_workspace_memory_candidate_scan(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
) -> None:
    payload = job.payload or {}
    session_id_value = payload.get("session_id")
    if session_id_value is None:
        raise ValueError("workspace-memory-candidate-scan requires session_id")
    session_id = UUID(str(session_id_value))
    limit_value = payload.get("max_candidates")
    max_candidates = 25
    if isinstance(limit_value, int | str):
        max_candidates = int(limit_value)
    candidates = WorkspaceMemoryCaptureService(
        cast(WorkspaceMemoryCaptureRepository, runtime_context.repositories.sessions)
    ).list_candidates(
        session_id,
        policy=MemoryExtractionPolicy(max_candidates=max_candidates),
    )
    record_background_job_progress(
        runtime_context,
        job,
        f"workspace memory scan found {len(candidates)} candidate(s)",
    )
    runtime_context.repositories.sessions.complete_background_job(
        job.job_id,
        summary=(
            f"Workspace memory candidate scan found {len(candidates)} "
            "review-gated candidate(s)."
        ),
    )


__all__ = ["run_read_only_background_job"]
