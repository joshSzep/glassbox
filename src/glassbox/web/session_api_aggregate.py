"""Operator aggregate response models for the session API."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.web.session_api_snapshot import SessionSummaryResponse


class OperatorSessionSummaryResponse(SessionSummaryResponse):
    queue_memberships: list[str]
    priority_bucket: str
    priority_rank: int
    action_needed: bool
    live_actionable: bool
    historical_only: bool
    has_active_turn: bool


class SessionQueueCountsResponse(BaseModel):
    total: int
    approvals: int
    questions: int
    failures: int
    degraded: int
    active: int
    action_needed: int
    historical: int


class ProjectionHealthCountsAggregateResponse(BaseModel):
    ok: int
    stale: int
    unavailable: int
    degraded: int


class WorkspaceRuntimeSummaryResponse(BaseModel):
    workspace_root: str
    state: str
    health: str | None
    pid: int | None
    dashboard_url: str | None
    health_url: str | None
    session_index_url: str | None
    started_at: datetime | None
    background_job_failed_count: int = 0
    background_job_retryable_count: int = 0
    background_job_abandoned_count: int = 0


class ProviderEvidenceSummaryResponse(BaseModel):
    advisory: bool = True
    summary_count: int = 0
    latest_summary_path: str | None = None
    latest_generated_at: str | None = None
    latest_status: str = "missing"
    freshness_status: str = "missing"
    freshness_policy_version: str = "provider-evidence-freshness.v1"
    stale_after_seconds: int = 604800
    schema_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    configured_model_name: str | None = None
    identity_matches_current_config: bool | None = None
    diagnostics_state: str | None = None
    scenario_count: int = 0
    matrix_entry_count: int = 0
    missing_scenarios: list[str] = Field(default_factory=list)
    passed_count: int = 0
    skipped_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    stale: bool = False
    next_actions: list[str] = Field(default_factory=list)


class SessionAggregateResponse(BaseModel):
    queue: str | None
    status: str | None
    sort: str
    limit: int | None
    queue_counts: SessionQueueCountsResponse
    projection_health_counts: ProjectionHealthCountsAggregateResponse
    runtime: WorkspaceRuntimeSummaryResponse
    provider_evidence: ProviderEvidenceSummaryResponse = Field(
        default_factory=ProviderEvidenceSummaryResponse
    )
    sessions: list[OperatorSessionSummaryResponse]
