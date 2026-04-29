"""Workspace observability summaries for operators and contributors."""

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.types import BackgroundJobState
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.branch_search import BranchSearchRepository
from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.transport import RuntimeEventTransportStats
from glassbox.services import SessionRepository
from glassbox.store.artifact_retention import inspect_artifact_state


class EventTransportObservability(BaseModel):
    """Live event delivery counters and reconnect guidance."""

    model_config = ConfigDict(extra="forbid")

    state: str
    subscriber_count: int
    dropped_events: int
    queue_capacity: int
    max_queue_depth: int
    queue_pressure: float
    last_published_sequence: int | None = None
    reconnect_mode: str
    reconnect_hint: str
    degraded: bool
    next_actions: list[str] = Field(default_factory=list)


class RuntimeObservability(BaseModel):
    """Runtime-owner health and live transport state."""

    model_config = ConfigDict(extra="forbid")

    state: str
    health: str | None
    dashboard_url: str | None = None
    health_url: str | None = None
    event_transport: EventTransportObservability
    next_actions: list[str] = Field(default_factory=list)


class ProjectionObservability(BaseModel):
    """Projection lag and repair guidance across retained sessions."""

    model_config = ConfigDict(extra="forbid")

    session_count: int
    ok_count: int
    stale_count: int
    unavailable_count: int
    degraded_count: int
    max_lag: int
    max_rebuild_event_count: int
    total_rebuild_event_count: int
    degraded_sessions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ArtifactObservability(BaseModel):
    """Managed artifact retention and storage-pressure summary."""

    model_config = ConfigDict(extra="forbid")

    protected_count: int
    candidate_count: int
    missing_reference_count: int
    reclaimable_bytes: int
    glassbox_size_bytes: int
    storage_warning_threshold_bytes: int | None = None
    storage_warning: str | None = None
    oldest_age_days: int | None = None
    category_counts: dict[str, int] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)


class VerificationObservability(BaseModel):
    """Retained eval-suite summary status."""

    model_config = ConfigDict(extra="forbid")

    summary_count: int
    latest_summary_path: str | None = None
    latest_suite_status: str | None = None
    latest_exit_code: int | None = None
    latest_profile_id: str | None = None
    latest_selected_case_count: int | None = None
    latest_passed_case_count: int | None = None
    latest_failed_case_count: int | None = None
    next_actions: list[str] = Field(default_factory=list)


class BackgroundJobObservability(BaseModel):
    """Projected daemon background job queue status."""

    model_config = ConfigDict(extra="forbid")

    pending_count: int
    running_count: int
    stale_count: int
    failed_count: int
    retryable_count: int
    abandoned_count: int
    last_failure_job_id: str | None = None
    last_failure_message: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class TaskAutonomyObservability(BaseModel):
    """Task-plan, verification, and autonomy-budget posture."""

    model_config = ConfigDict(extra="forbid")

    task_count: int
    active_count: int
    blocked_count: int
    failed_count: int
    budget_exhausted_count: int
    verification_failed_count: int
    latest_blocked_task_id: str | None = None
    latest_failed_task_id: str | None = None
    latest_budget_exhausted_task_id: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class WorkspaceMemoryObservability(BaseModel):
    """Workspace-memory freshness and cleanup posture."""

    model_config = ConfigDict(extra="forbid")

    active_count: int
    stale_count: int
    imported_count: int
    invalidated_count: int
    pruned_count: int
    redacted_count: int
    last_invalidated_memory_id: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class RepositoryIndexObservability(BaseModel):
    """Repository-index freshness and rebuild posture."""

    model_config = ConfigDict(extra="forbid")

    status: str
    path: str
    entry_count: int
    built_at: str | None = None
    failure_reason: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class BranchSearchObservability(BaseModel):
    """Branch-search queue and candidate review posture."""

    model_config = ConfigDict(extra="forbid")

    search_count: int
    active_count: int
    completed_count: int
    abandoned_count: int
    needs_review_count: int
    failed_verification_count: int
    selected_count: int
    latest_search_id: str | None = None
    latest_needs_review_search_id: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class WorkspaceObservabilityReport(BaseModel):
    """Operator-facing summary of workspace health and inspection paths."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    runtime: RuntimeObservability
    projections: ProjectionObservability
    tasks: TaskAutonomyObservability
    background_jobs: BackgroundJobObservability
    memory: WorkspaceMemoryObservability
    repository_index: RepositoryIndexObservability
    branch_searches: BranchSearchObservability
    artifacts: ArtifactObservability
    verification: VerificationObservability
    provider_canary: ProviderCanaryEvidenceSummary
    next_actions: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _RetainedEvalSummary:
    path: Path
    payload: dict[str, Any]


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
    memory = build_workspace_memory_observability(session_repository)
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


def build_runtime_observability(
    runtime_status: RuntimeOwnerStatus,
    *,
    event_transport_stats: RuntimeEventTransportStats,
    workspace_root: Path,
) -> RuntimeObservability:
    record = runtime_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    health_url = _health_url(dashboard_url)
    event_transport = build_event_transport_observability(event_transport_stats)
    quoted_workspace_root = shlex.quote(str(workspace_root))
    next_actions: list[str] = []
    if runtime_status.state == "not_running":
        next_actions.append(f"glassbox daemon start --cwd {quoted_workspace_root}")
    elif runtime_status.state == "stale":
        next_actions.append(f"glassbox daemon stop --cwd {quoted_workspace_root}")
        next_actions.append(f"glassbox daemon start --cwd {quoted_workspace_root}")
    elif runtime_status.health != "ok":
        next_actions.append(f"inspect runtime health at {health_url}")
    next_actions.extend(event_transport.next_actions)
    return RuntimeObservability(
        state=runtime_status.state,
        health=runtime_status.health,
        dashboard_url=dashboard_url,
        health_url=health_url,
        event_transport=event_transport,
        next_actions=next_actions,
    )


def build_event_transport_observability(
    stats: RuntimeEventTransportStats,
) -> EventTransportObservability:
    next_actions: list[str] = []
    queue_pressure = _queue_pressure(stats.max_queue_depth, stats.queue_capacity)
    if stats.dropped_events > 0:
        next_actions.append(
            "refresh live clients or reconnect with the last observed sequence"
        )
    if queue_pressure >= 1:
        next_actions.append(
            "inspect slow live subscribers and reconnect lagging clients"
        )
    degraded = stats.dropped_events > 0 or queue_pressure >= 1
    return EventTransportObservability(
        state="degraded" if degraded else "healthy",
        subscriber_count=stats.subscriber_count,
        dropped_events=stats.dropped_events,
        queue_capacity=stats.queue_capacity,
        max_queue_depth=stats.max_queue_depth,
        queue_pressure=queue_pressure,
        last_published_sequence=stats.last_published_sequence,
        reconnect_mode="resume with /sessions/{session_id}/events?after=SEQUENCE",
        reconnect_hint=_reconnect_hint(stats.last_published_sequence),
        degraded=degraded,
        next_actions=next_actions,
    )


def _queue_pressure(max_queue_depth: int, queue_capacity: int) -> float:
    if queue_capacity <= 0:
        return 0.0
    return round(max_queue_depth / queue_capacity, 3)


def _reconnect_hint(last_published_sequence: int | None) -> str:
    if last_published_sequence is None:
        return "use the client's last observed sequence as the after cursor"
    return (
        f"latest published sequence is {last_published_sequence}; reconnect after "
        "the client's last observed sequence"
    )


def build_projection_observability(
    session_repository: SessionRepository,
) -> ProjectionObservability:
    sessions = session_repository.list_sessions()
    counts = {"ok": 0, "stale": 0, "unavailable": 0}
    degraded_sessions: list[str] = []
    max_lag = 0
    max_rebuild_event_count = 0
    total_rebuild_event_count = 0
    for session in sessions:
        health = session_repository.inspect_session_projection_health(
            session.session_id
        )
        counts[health.state] = counts.get(health.state, 0) + 1
        max_lag = max(max_lag, health.lag)
        max_rebuild_event_count = max(
            max_rebuild_event_count,
            health.estimated_rebuild_event_count,
        )
        if health.degraded:
            degraded_sessions.append(str(session.session_id))
            total_rebuild_event_count += health.estimated_rebuild_event_count

    next_actions: list[str] = []
    if degraded_sessions:
        next_actions.append("glassbox projection check --all")
        next_actions.append("glassbox projection rebuild --all")
    return ProjectionObservability(
        session_count=len(sessions),
        ok_count=counts.get("ok", 0),
        stale_count=counts.get("stale", 0),
        unavailable_count=counts.get("unavailable", 0),
        degraded_count=len(degraded_sessions),
        max_lag=max_lag,
        max_rebuild_event_count=max_rebuild_event_count,
        total_rebuild_event_count=total_rebuild_event_count,
        degraded_sessions=degraded_sessions,
        next_actions=next_actions,
    )


def build_artifact_observability(
    workspace_root: Path,
    session_repository: SessionRepository,
) -> ArtifactObservability:
    report = inspect_artifact_state(workspace_root, session_repository)
    next_actions: list[str] = []
    if report.storage_warning is not None or report.candidates:
        next_actions.append("glassbox artifacts inspect")
        next_actions.append("glassbox artifacts prune --dry-run")
    return ArtifactObservability(
        protected_count=len(report.protected),
        candidate_count=len(report.candidates),
        missing_reference_count=len(report.missing_references),
        reclaimable_bytes=report.candidate_size_bytes,
        glassbox_size_bytes=report.glassbox_size_bytes,
        storage_warning_threshold_bytes=report.storage_warning_threshold_bytes,
        storage_warning=report.storage_warning,
        oldest_age_days=report.oldest_age_days,
        category_counts=report.category_counts,
        next_actions=next_actions,
    )


def build_background_job_observability(
    session_repository: SessionRepository,
) -> BackgroundJobObservability:
    counts = session_repository.count_background_jobs_by_state()
    pending_count = counts.get("queued", 0) + counts.get(
        "cancellation_requested",
        0,
    )
    running_count = counts.get("claimed", 0) + counts.get("running", 0)
    stale_count = counts.get("stale", 0)
    failed_count = counts.get("failed", 0)
    abandoned_count = counts.get("abandoned", 0)
    last_failure = session_repository.latest_failed_background_job()
    retryable_count = len(
        [
            job
            for job in session_repository.list_background_jobs(
                state=BackgroundJobState.FAILED
            )
            if job.retryable
        ]
    )
    next_actions: list[str] = []
    if pending_count:
        next_actions.append("glassbox job list --state queued")
    if running_count:
        next_actions.append("glassbox job list --state running")
    if stale_count:
        next_actions.append("glassbox job list --state stale")
    if retryable_count:
        next_actions.append("glassbox job list --state failed")
    if last_failure is not None:
        next_actions.append(f"glassbox job show {last_failure.job_id}")
    return BackgroundJobObservability(
        pending_count=pending_count,
        running_count=running_count,
        stale_count=stale_count,
        failed_count=failed_count,
        retryable_count=retryable_count,
        abandoned_count=abandoned_count,
        last_failure_job_id=(str(last_failure.job_id) if last_failure else None),
        last_failure_message=(last_failure.failure_message if last_failure else None),
        next_actions=next_actions,
    )


def build_task_autonomy_observability(
    session_repository: SessionRepository,
) -> TaskAutonomyObservability:
    task_repository = cast(TaskPlanRepository, session_repository)
    tasks = task_repository.list_tasks()
    active_tasks = [task for task in tasks if task.status == TaskPlanStatus.ACTIVE]
    blocked_tasks = [
        task
        for task in tasks
        if task.status == TaskPlanStatus.PAUSED or task.blocked_reason is not None
    ]
    failed_tasks = [task for task in tasks if task.status == TaskPlanStatus.FAILED]
    budget_exhausted_tasks = []
    for task in tasks:
        posture = session_repository.get_budget_posture(
            task.session_id,
            task_id=task.task_id,
        )
        if posture is not None and posture.last_reason == "budget_exhausted":
            budget_exhausted_tasks.append(task)
    verification_failed_count = 0
    for task in tasks:
        verification_failed_count += sum(
            1
            for verification in task_repository.list_task_verifications(
                task.session_id,
                task.task_id,
            )
            if verification.status == TaskVerificationStatus.FAILED
        )

    latest_blocked = _latest_task(blocked_tasks)
    latest_failed = _latest_task(failed_tasks)
    latest_budget_exhausted = _latest_task(budget_exhausted_tasks)
    next_actions: list[str] = []
    if active_tasks:
        next_actions.append("glassbox task list")
    if latest_blocked is not None:
        next_actions.append(f"glassbox task show {latest_blocked.task_id}")
    if latest_budget_exhausted is not None:
        next_actions.append(
            f"glassbox task continue {latest_budget_exhausted.task_id} --verify-repair"
        )
    if latest_failed is not None:
        next_actions.append(f"glassbox task show {latest_failed.task_id}")

    return TaskAutonomyObservability(
        task_count=len(tasks),
        active_count=len(active_tasks),
        blocked_count=len(blocked_tasks),
        failed_count=len(failed_tasks),
        budget_exhausted_count=len(budget_exhausted_tasks),
        verification_failed_count=verification_failed_count,
        latest_blocked_task_id=(
            str(latest_blocked.task_id) if latest_blocked is not None else None
        ),
        latest_failed_task_id=(
            str(latest_failed.task_id) if latest_failed is not None else None
        ),
        latest_budget_exhausted_task_id=(
            str(latest_budget_exhausted.task_id)
            if latest_budget_exhausted is not None
            else None
        ),
        next_actions=_dedupe(next_actions),
    )


def build_workspace_memory_observability(
    session_repository: SessionRepository,
) -> WorkspaceMemoryObservability:
    entries = session_repository.list_workspace_memory(include_pruned=True)
    counts = {state.value: 0 for state in WorkspaceMemoryState}
    redacted_count = 0
    invalidated_entries = []
    for entry in entries:
        counts[entry.state.value] = counts.get(entry.state.value, 0) + 1
        if entry.redacted:
            redacted_count += 1
        if entry.state == WorkspaceMemoryState.INVALIDATED:
            invalidated_entries.append(entry)

    latest_invalidated = max(
        invalidated_entries,
        key=lambda entry: entry.updated_at,
        default=None,
    )
    next_actions: list[str] = []
    if counts.get("stale", 0):
        next_actions.append("glassbox memory list --state stale")
        next_actions.append(
            "glassbox memory invalidate MEMORY_ID --reason 'stale memory reviewed'"
        )
    if counts.get("imported", 0):
        next_actions.append("glassbox memory list --state imported")
        next_actions.append("glassbox memory confirm MEMORY_ID")
    if counts.get("invalidated", 0):
        next_actions.append("glassbox memory list --state invalidated")
        next_actions.append(
            "glassbox memory prune MEMORY_ID --dry-run --reason 'validated cleanup'"
        )

    return WorkspaceMemoryObservability(
        active_count=counts.get("active", 0),
        stale_count=counts.get("stale", 0),
        imported_count=counts.get("imported", 0),
        invalidated_count=counts.get("invalidated", 0),
        pruned_count=counts.get("pruned", 0),
        redacted_count=redacted_count,
        last_invalidated_memory_id=(
            str(latest_invalidated.memory_id)
            if latest_invalidated is not None
            else None
        ),
        next_actions=next_actions,
    )


def build_repository_index_observability(
    workspace_root: Path,
) -> RepositoryIndexObservability:
    path = repository_index_path(workspace_root)
    quoted_workspace_root = shlex.quote(str(workspace_root))
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return RepositoryIndexObservability(
            status="missing",
            path=str(path),
            entry_count=0,
            next_actions=[f"glassbox repo index build --cwd {quoted_workspace_root}"],
        )

    next_actions: list[str] = []
    if snapshot.status in {
        RepositoryIndexFreshness.STALE,
        RepositoryIndexFreshness.FAILED,
    }:
        next_actions.append(f"glassbox repo index status --cwd {quoted_workspace_root}")
        next_actions.append(f"glassbox repo index build --cwd {quoted_workspace_root}")
    elif snapshot.status == RepositoryIndexFreshness.BUILDING:
        next_actions.append(f"glassbox repo index status --cwd {quoted_workspace_root}")

    return RepositoryIndexObservability(
        status=snapshot.status.value,
        path=str(path),
        entry_count=len(snapshot.entries),
        built_at=snapshot.built_at.isoformat() if snapshot.built_at else None,
        failure_reason=snapshot.failure_reason,
        next_actions=next_actions,
    )


def build_branch_search_observability(
    session_repository: SessionRepository,
) -> BranchSearchObservability:
    branch_repository = cast(BranchSearchRepository, session_repository)
    searches = branch_repository.list_branch_searches()
    active_searches = [
        search
        for search in searches
        if search.status in {BranchSearchStatus.STARTED, BranchSearchStatus.RUNNING}
    ]
    completed_count = sum(
        1 for search in searches if search.status == BranchSearchStatus.COMPLETED
    )
    abandoned_count = sum(
        1 for search in searches if search.status == BranchSearchStatus.ABANDONED
    )
    needs_review_count = 0
    failed_verification_count = 0
    selected_count = 0
    latest_needs_review_search_id: str | None = None
    for search in searches:
        candidates = branch_repository.list_branch_candidates(
            search.session_id,
            search.search_id,
        )
        for candidate in candidates:
            if candidate.status.value == "needs_review":
                needs_review_count += 1
                latest_needs_review_search_id = str(search.search_id)
            if candidate.verification_status in {
                BranchCandidateVerificationStatus.FAILED,
                BranchCandidateVerificationStatus.BLOCKED,
                BranchCandidateVerificationStatus.TIMED_OUT,
            }:
                failed_verification_count += 1
            if candidate.selection_state is not None:
                selected_count += int(candidate.selection_state.value == "selected")

    latest_search = max(searches, key=lambda search: search.updated_at, default=None)
    next_actions: list[str] = []
    if active_searches:
        next_actions.append("glassbox branch-search list")
    if latest_needs_review_search_id is not None:
        next_actions.append(
            f"glassbox branch-search show {latest_needs_review_search_id}"
        )
        next_actions.append(
            "glassbox branch-search reject SEARCH_ID CANDIDATE_ID --reason 'cleanup'"
        )
    if failed_verification_count:
        next_actions.append("glassbox branch-search list")

    return BranchSearchObservability(
        search_count=len(searches),
        active_count=len(active_searches),
        completed_count=completed_count,
        abandoned_count=abandoned_count,
        needs_review_count=needs_review_count,
        failed_verification_count=failed_verification_count,
        selected_count=selected_count,
        latest_search_id=str(latest_search.search_id) if latest_search else None,
        latest_needs_review_search_id=latest_needs_review_search_id,
        next_actions=_dedupe(next_actions),
    )


def build_verification_observability(workspace_root: Path) -> VerificationObservability:
    summaries = _retained_eval_summaries(workspace_root)
    if not summaries:
        return VerificationObservability(
            summary_count=0,
            next_actions=["glassbox eval run"],
        )

    latest_summary = summaries[0]
    latest_path = latest_summary.path
    payload = latest_summary.payload
    latest_exit_code = _optional_int(payload.get("exit_code"))
    latest_profile_id = _optional_str(payload.get("profile_id"))
    latest_suite_status = "passed" if latest_exit_code == 0 else "failed"
    next_actions = [f"inspect eval summary {latest_path}"]
    if latest_exit_code not in (None, 0):
        next_actions.append(f"glassbox eval report {latest_profile_id or 'PROFILE_ID'}")

    return VerificationObservability(
        summary_count=len(summaries),
        latest_summary_path=str(latest_path),
        latest_suite_status=latest_suite_status,
        latest_exit_code=latest_exit_code,
        latest_profile_id=latest_profile_id,
        latest_selected_case_count=_optional_int(payload.get("selected_case_count")),
        latest_passed_case_count=_optional_int(payload.get("passed_case_count")),
        latest_failed_case_count=_optional_int(payload.get("failed_case_count")),
        next_actions=next_actions,
    )


def _retained_eval_summaries(workspace_root: Path) -> list[_RetainedEvalSummary]:
    summary_paths = sorted(
        (workspace_root / ".glassbox" / "evals").glob("**/summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [
        _RetainedEvalSummary(path=path, payload=_load_json_object(path))
        for path in summary_paths
    ]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _health_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    return dashboard_url.rstrip("/") + "/healthz"


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _latest_task(tasks):
    return max(tasks, key=lambda task: task.updated_at, default=None)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
