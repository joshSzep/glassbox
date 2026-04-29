"""Structured observability report models."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary


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
]
