"""Unit tests for workspace and release handoff readiness summaries."""

from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadinessState
from glassbox.runtime import workspace_handoff_readiness_release as release_helper
from glassbox.runtime import workspace_handoff_readiness_workspace as workspace_helper
from glassbox.runtime.observability_models import ArtifactObservability
from glassbox.runtime.observability_models import BackgroundJobObservability
from glassbox.runtime.observability_models import BranchSearchObservability
from glassbox.runtime.observability_models import EventTransportObservability
from glassbox.runtime.observability_models import ProjectionObservability
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import RepositoryIntelligenceObservability
from glassbox.runtime.observability_models import RuntimeObservability
from glassbox.runtime.observability_models import TaskAutonomyObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.observability_models import WorkspaceObservabilityReport
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)


def test_workspace_handoff_readiness_ready_for_future_self() -> None:
    report = _report()

    readiness = derive_workspace_handoff_readiness(
        report,
        intent=HandoffIntent.FUTURE_SELF,
    )

    assert readiness.source.kind == "workspace"
    assert readiness.state == HandoffReadinessState.READY
    assert readiness.safe_first_commands
    assert all(command.read_only for command in readiness.safe_first_commands)
    assert "does not approve" in readiness.non_claims[1]


def test_workspace_handoff_readiness_public_entrypoint_uses_workspace_helper() -> None:
    report = _report()

    public_readiness = derive_workspace_handoff_readiness(report)
    helper_readiness = workspace_helper.derive_workspace_handoff_readiness(report)

    assert public_readiness.model_dump() == helper_readiness.model_dump()


def test_workspace_handoff_readiness_surfaces_failed_work() -> None:
    report = _report(
        tasks=TaskAutonomyObservability.model_construct(
            task_count=3,
            active_count=1,
            blocked_count=0,
            failed_count=1,
            budget_exhausted_count=0,
            verification_failed_count=0,
            latest_failed_task_id="task-123",
            next_actions=[],
        )
    )

    readiness = derive_workspace_handoff_readiness(report)

    assert readiness.state == HandoffReadinessState.FAILED_NEEDS_TRIAGE
    assert any("failed task" in reason.summary for reason in readiness.reasons)


def test_release_handoff_readiness_requires_retained_eval_summary() -> None:
    report = _report(
        verification=VerificationObservability.model_construct(
            summary_count=0,
            latest_summary_path=None,
            latest_suite_status=None,
            latest_exit_code=None,
            latest_profile_id=None,
            latest_selected_case_count=None,
            latest_passed_case_count=None,
            latest_failed_case_count=None,
            next_actions=[],
        )
    )

    readiness = derive_release_handoff_readiness(report)

    assert readiness.source.kind == "release"
    assert readiness.intent == HandoffIntent.RELEASE_SIGNOFF
    assert readiness.state == HandoffReadinessState.NEEDS_VERIFICATION
    assert any(
        item.ref_id == "release-eval-summary" for item in readiness.missing_evidence
    )
    assert "not release approval" in readiness.non_claims[1]


def test_release_handoff_readiness_marks_failed_eval_needs_verification() -> None:
    report = _report(
        verification=VerificationObservability.model_construct(
            summary_count=1,
            latest_summary_path=".glassbox/evals/latest/summary.json",
            latest_suite_status="failed",
            latest_exit_code=1,
            latest_profile_id="release-candidate",
            latest_selected_case_count=2,
            latest_passed_case_count=1,
            latest_failed_case_count=1,
            next_actions=[],
        )
    )

    readiness = derive_release_handoff_readiness(report)

    assert readiness.state == HandoffReadinessState.NEEDS_VERIFICATION
    assert any("failed" in reason.summary for reason in readiness.reasons)


def test_release_handoff_readiness_public_entrypoint_uses_release_helper() -> None:
    report = _report()

    public_readiness = derive_release_handoff_readiness(report)
    helper_readiness = release_helper.derive_release_handoff_readiness(report)

    assert public_readiness.model_dump() == helper_readiness.model_dump()


def _report(
    *,
    runtime: RuntimeObservability | None = None,
    projections: ProjectionObservability | None = None,
    tasks: TaskAutonomyObservability | None = None,
    background_jobs: BackgroundJobObservability | None = None,
    memory: WorkspaceMemoryObservability | None = None,
    repository_index: RepositoryIndexObservability | None = None,
    repository_intelligence: RepositoryIntelligenceObservability | None = None,
    branch_searches: BranchSearchObservability | None = None,
    artifacts: ArtifactObservability | None = None,
    verification: VerificationObservability | None = None,
    provider_canary: ProviderCanaryEvidenceSummary | None = None,
) -> WorkspaceObservabilityReport:
    return WorkspaceObservabilityReport.model_construct(
        workspace_root="/tmp/workspace",
        runtime=runtime or _runtime(),
        projections=projections or _projections(),
        tasks=tasks or _tasks(),
        background_jobs=background_jobs or _background_jobs(),
        memory=memory or _memory(),
        repository_index=repository_index or _repository_index(),
        repository_intelligence=repository_intelligence or _repository_intelligence(),
        branch_searches=branch_searches or _branch_searches(),
        artifacts=artifacts or _artifacts(),
        verification=verification or _verification(),
        provider_canary=provider_canary or _provider_canary(),
        maintenance_cues=[],
        recovery_playbooks=[],
        next_actions=[],
    )


def _runtime() -> RuntimeObservability:
    return RuntimeObservability.model_construct(
        state="not_running",
        health=None,
        dashboard_url=None,
        health_url=None,
        event_transport=EventTransportObservability.model_construct(
            state="healthy",
            subscriber_count=0,
            dropped_events=0,
            queue_capacity=64,
            max_queue_depth=0,
            queue_pressure=0.0,
            last_published_sequence=None,
            reconnect_mode="resume with last observed sequence",
            reconnect_hint="last observed sequence unavailable",
            degraded=False,
            next_actions=[],
        ),
        next_actions=[],
    )


def _projections() -> ProjectionObservability:
    return ProjectionObservability.model_construct(
        session_count=1,
        ok_count=1,
        stale_count=0,
        unavailable_count=0,
        degraded_count=0,
        max_lag=0,
        max_rebuild_event_count=0,
        total_rebuild_event_count=0,
        degraded_sessions=[],
        next_actions=[],
    )


def _tasks() -> TaskAutonomyObservability:
    return TaskAutonomyObservability.model_construct(
        task_count=0,
        active_count=0,
        blocked_count=0,
        failed_count=0,
        budget_exhausted_count=0,
        verification_failed_count=0,
        latest_blocked_task_id=None,
        latest_failed_task_id=None,
        latest_budget_exhausted_task_id=None,
        next_actions=[],
    )


def _background_jobs() -> BackgroundJobObservability:
    return BackgroundJobObservability.model_construct(
        pending_count=0,
        running_count=0,
        stale_count=0,
        failed_count=0,
        retryable_count=0,
        abandoned_count=0,
        last_failure_job_id=None,
        last_failure_message=None,
        next_actions=[],
    )


def _memory() -> WorkspaceMemoryObservability:
    return WorkspaceMemoryObservability.model_construct(
        active_count=0,
        stale_count=0,
        imported_count=0,
        invalidated_count=0,
        pruned_count=0,
        redacted_count=0,
        conflict_count=0,
        conflicted_memory_ids=[],
        last_invalidated_memory_id=None,
        next_actions=[],
    )


def _repository_index() -> RepositoryIndexObservability:
    return RepositoryIndexObservability.model_construct(
        status="fresh",
        path="/tmp/workspace/.glassbox/repository-index.json",
        entry_count=10,
        built_at="2026-05-16T00:00:00Z",
        failure_reason=None,
        detail=None,
        stale_reason=None,
        next_actions=[],
    )


def _repository_intelligence() -> RepositoryIntelligenceObservability:
    return RepositoryIntelligenceObservability.model_construct(
        status="fresh",
        index_status="fresh",
        topology_status="fresh",
        command_recipe_status="fresh",
        memory_conflict_status="clean",
        eval_metadata_status="fresh",
        release_surface_status="fresh",
        cue_count=0,
        warning_count=0,
        missing_count=0,
        freshness_cues=[],
        next_actions=[],
    )


def _branch_searches() -> BranchSearchObservability:
    return BranchSearchObservability.model_construct(
        search_count=0,
        active_count=0,
        completed_count=0,
        abandoned_count=0,
        needs_review_count=0,
        failed_verification_count=0,
        selected_count=0,
        latest_search_id=None,
        latest_needs_review_search_id=None,
        next_actions=[],
    )


def _artifacts() -> ArtifactObservability:
    return ArtifactObservability.model_construct(
        protected_count=0,
        candidate_count=0,
        missing_reference_count=0,
        reclaimable_bytes=0,
        glassbox_size_bytes=0,
        storage_warning_threshold_bytes=None,
        storage_warning=None,
        oldest_age_days=None,
        category_counts={},
        next_actions=[],
    )


def _verification() -> VerificationObservability:
    return VerificationObservability.model_construct(
        summary_count=1,
        latest_summary_path=".glassbox/evals/latest/summary.json",
        latest_suite_status="passed",
        latest_exit_code=0,
        latest_profile_id="release-candidate",
        latest_selected_case_count=2,
        latest_passed_case_count=2,
        latest_failed_case_count=0,
        next_actions=[],
    )


def _provider_canary() -> ProviderCanaryEvidenceSummary:
    return ProviderCanaryEvidenceSummary.model_construct(
        summary_count=0,
        latest_summary_path=None,
        latest_generated_at=None,
        latest_status="missing",
        freshness_status="missing",
        stale=False,
        next_actions=[],
    )
