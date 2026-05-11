"""Detail, inventory, and verification response builders."""

from collections.abc import Sequence

from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ChangesetVerificationPlanLifecycleSummary
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.web.changeset_api_builders_review import build_manual_evidence_response
from glassbox.web.changeset_api_builders_review import build_review_feedback_response
from glassbox.web.changeset_api_builders_review import (
    build_review_response_summary_response,
)
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceItemResponse
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceSummaryResponse
from glassbox.web.changeset_api_models import ChangesetDetailResponse
from glassbox.web.changeset_api_models import ChangesetInventoryResponse
from glassbox.web.changeset_api_models import ChangesetInventoryStatusResponse
from glassbox.web.changeset_api_models import ChangesetReadinessResponse
from glassbox.web.changeset_api_models import ChangesetReviewBriefGenerateResponse
from glassbox.web.changeset_api_models import ChangesetReviewBriefResponse
from glassbox.web.changeset_api_models import ChangesetSourceResponse
from glassbox.web.changeset_api_models import ChangesetSummaryResponse
from glassbox.web.changeset_api_models import ChangesetTopologyImpactResponse
from glassbox.web.changeset_api_models import (
    ChangesetVerificationPlanEntrySummaryResponse,
)
from glassbox.web.changeset_api_models import (
    ChangesetVerificationPlanLifecycleSummaryResponse,
)
from glassbox.web.changeset_api_models import ChangesetVerificationPlanPreviewResponse
from glassbox.web.changeset_api_models import ChangesetVerificationPostureResponse
from glassbox.web.changeset_api_models import ChangesetVerificationReadinessResponse
from glassbox.web.changeset_api_models import ChangesetVerificationReasonGroupResponse
from glassbox.web.changeset_api_models import ChangesetVerificationRecipePreviewResponse
from glassbox.web.changeset_api_models import ChangesetVerificationRequirementResponse
from glassbox.web.changeset_api_models import (
    ChangesetVerificationReviewLoopSummaryResponse,
)
from glassbox.web.changeset_api_models import ChangesetVerificationSkippedCheckResponse
from glassbox.web.changeset_api_models import VerificationPlanCommandRecipeResponse
from glassbox.web.changeset_api_models import VerificationPlanEntryResponse
from glassbox.web.changeset_api_models import VerificationPlanEvidenceRefResponse
from glassbox.web.changeset_api_models import VerificationPlanTargetResponse


def build_changeset_summary_response(
    changeset: ChangesetRecord,
) -> ChangesetSummaryResponse:
    return ChangesetSummaryResponse(
        session_id=str(changeset.session_id),
        changeset_id=str(changeset.changeset_id),
        objective=changeset.objective,
        summary=changeset.summary,
        status=changeset.status,
        created_by=changeset.created_by,
        archived_by=changeset.archived_by,
        archived_reason=changeset.archived_reason,
        replacement_changeset_id=_optional_str(changeset.replacement_changeset_id),
        task_id=_optional_str(changeset.task_id),
        turn_id=_optional_str(changeset.turn_id),
        branch_search_id=_optional_str(changeset.branch_search_id),
        branch_candidate_id=_optional_str(changeset.branch_candidate_id),
        latest_inventory_artifact_id=_optional_str(
            changeset.latest_inventory_artifact_id
        ),
        latest_verification_id=_optional_str(changeset.latest_verification_id),
        latest_review_brief_artifact_id=_optional_str(
            changeset.latest_review_brief_artifact_id
        ),
        risk_level=changeset.risk_level.value,
        risk_summary=changeset.risk_summary,
        unresolved_risk_count=changeset.unresolved_risk_count,
        accepted_risk_count=changeset.accepted_risk_count,
        created_at=changeset.created_at,
        updated_at=changeset.updated_at,
        last_sequence=changeset.last_sequence,
    )


def build_changeset_summary_responses(
    changesets: Sequence[ChangesetRecord],
) -> list[ChangesetSummaryResponse]:
    return [build_changeset_summary_response(item) for item in changesets]


def build_changeset_detail_response(
    detail: ChangesetDetailView,
) -> ChangesetDetailResponse:
    return ChangesetDetailResponse(
        changeset=build_changeset_summary_response(detail.changeset),
        sources=[build_changeset_source_response(item) for item in detail.sources],
        inventory=(
            build_changeset_inventory_response(detail.inventory)
            if detail.inventory is not None
            else None
        ),
        inventory_status=ChangesetInventoryStatusResponse(
            freshness=detail.inventory_status.freshness.value,
            stale=detail.inventory_status.stale,
            reason=detail.inventory_status.reason,
            recorded_source_digest=detail.inventory_status.recorded_source_digest,
            current_source_digest=detail.inventory_status.current_source_digest,
            safe_next_actions=detail.inventory_status.safe_next_actions,
        ),
        verification_posture=(
            build_changeset_verification_posture_response(detail.verification_posture)
            if detail.verification_posture is not None
            else None
        ),
        review_briefs=[
            build_changeset_review_brief_response(item) for item in detail.review_briefs
        ],
        review_feedback=[
            build_review_feedback_response(item) for item in detail.review_feedback
        ],
        manual_evidence=[
            build_manual_evidence_response(item) for item in detail.manual_evidence
        ],
        review_response_summary=build_review_response_summary_response(
            detail.review_response_summary
        ),
        readiness=[
            build_changeset_readiness_response(item) for item in detail.readiness
        ],
        command_evidence=ChangesetCommandEvidenceSummaryResponse(
            total_count=detail.command_evidence.total_count,
            verification_count=detail.command_evidence.verification_count,
            failed_count=detail.command_evidence.failed_count,
            risky_count=detail.command_evidence.risky_count,
            environment_captured_count=(
                detail.command_evidence.environment_captured_count
            ),
            artifact_count=detail.command_evidence.artifact_count,
            items=[
                ChangesetCommandEvidenceItemResponse(
                    tool_attempt_id=item.tool_attempt_id,
                    turn_id=item.turn_id,
                    task_id=item.task_id,
                    tool_name=item.tool_name,
                    status=item.status,
                    purpose=item.purpose,
                    review_relevance=item.review_relevance,
                    supports_verification=item.supports_verification,
                    summary=item.summary,
                    output_artifact_id=_optional_str(item.output_artifact_id),
                    environment_captured=item.environment_captured,
                    toolchain_count=item.toolchain_count,
                    redaction_notes=item.redaction_notes,
                    policy_summary=item.policy_summary,
                    local_only=item.local_only,
                )
                for item in detail.command_evidence.items
            ],
            limitations=detail.command_evidence.limitations,
            safe_next_actions=detail.command_evidence.safe_next_actions,
        ),
        verification_plan_summary=build_changeset_verification_plan_summary_response(
            detail.verification_plan_summary
        ),
        limitations=detail.limitations,
        safe_next_actions=detail.safe_next_actions,
    )


def build_changeset_verification_plan_response(
    preview: ChangesetVerificationPlanPreview,
) -> ChangesetVerificationPlanPreviewResponse:
    return ChangesetVerificationPlanPreviewResponse(
        changeset_id=str(preview.changeset_id),
        session_id=str(preview.session_id),
        inventory_artifact_id=_optional_str(preview.inventory_artifact_id),
        inventory_freshness=preview.inventory_freshness.value,
        changed_paths=preview.changed_paths,
        plan_entries=[
            build_verification_plan_entry_response(entry)
            for entry in preview.plan_entries
        ],
        skipped_checks=[
            ChangesetVerificationSkippedCheckResponse(
                target_id=skipped.target_id,
                target_kind=skipped.target_kind,
                reason=skipped.reason,
                explanation=skipped.explanation,
                matched_paths=skipped.matched_paths,
                safe_next_actions=skipped.safe_next_actions,
            )
            for skipped in preview.skipped_checks
        ],
        recommended_commands=preview.recommended_commands,
        eval_profiles=preview.eval_profiles,
        recipes=[
            ChangesetVerificationRecipePreviewResponse(
                recipe_id=recipe.recipe_id,
                title=recipe.title,
                confidence=recipe.confidence,
                source=recipe.source,
                matched_paths=recipe.matched_paths,
                component_ids=recipe.component_ids,
                commands=recipe.commands,
                profile_ids=recipe.profile_ids,
                case_ids=recipe.case_ids,
                notes=recipe.notes,
                limitations=recipe.limitations,
            )
            for recipe in preview.recipes
        ],
        topology_impacts=[
            ChangesetTopologyImpactResponse(
                component_id=impact.component_id,
                name=impact.name,
                kind=impact.kind,
                root_path=impact.root_path,
                matched_paths=impact.matched_paths,
                test_roots=impact.test_roots,
                ownership_hints=impact.ownership_hints,
                dependency_hints=impact.dependency_hints,
                topology_freshness=impact.topology_freshness,
                recommendation_posture=impact.recommendation_posture,
                limitations=impact.limitations,
            )
            for impact in preview.topology_impacts
        ],
        review_loop_summary=build_verification_review_loop_summary_response(
            preview.review_loop_summary
        ),
        reason_groups=[
            ChangesetVerificationReasonGroupResponse(
                group=group.group,
                title=group.title,
                summaries=group.summaries,
                matched_paths=group.matched_paths,
                rule_ids=group.rule_ids,
                recommended_case_ids=group.recommended_case_ids,
                recommended_profile_ids=group.recommended_profile_ids,
                release_gate_commands=group.release_gate_commands,
            )
            for group in preview.reason_groups
        ],
        expected_scope=preview.expected_scope,
        retained_artifact_ids=[
            str(artifact_id) for artifact_id in preview.retained_artifact_ids
        ],
        readiness=build_changeset_verification_readiness_response(preview.readiness),
        plan_summary=build_changeset_verification_plan_summary_response(
            preview.plan_summary
        ),
        limitations=preview.limitations,
        safe_next_actions=preview.safe_next_actions,
        non_claims=preview.non_claims,
    )


def build_changeset_verification_plan_summary_response(
    summary: ChangesetVerificationPlanLifecycleSummary,
) -> ChangesetVerificationPlanLifecycleSummaryResponse:
    return ChangesetVerificationPlanLifecycleSummaryResponse(
        total_count=summary.total_count,
        proposed_count=summary.proposed_count,
        selected_count=summary.selected_count,
        running_count=summary.running_count,
        passed_count=summary.passed_count,
        failed_count=summary.failed_count,
        skipped_count=summary.skipped_count,
        stale_count=summary.stale_count,
        accepted_risk_count=summary.accepted_risk_count,
        manual_only_count=summary.manual_only_count,
        command_count=summary.command_count,
        latest_verification_id=_optional_str(summary.latest_verification_id),
        latest_status=summary.latest_status,
        entries=[
            ChangesetVerificationPlanEntrySummaryResponse(
                verification_id=str(entry.verification_id),
                check_name=entry.check_name,
                status=entry.status,
                lifecycle_state=entry.lifecycle_state,
                kind=entry.kind,
                source=entry.source,
                command=entry.command,
                changed_paths=entry.changed_paths,
                blocking=entry.blocking,
                reason=entry.reason,
                artifact_id=_optional_str(entry.artifact_id),
                failed_artifact_id=_optional_str(entry.failed_artifact_id),
                failure_summary=entry.failure_summary,
                accepted_risk_count=entry.accepted_risk_count,
                accepted_risks=entry.accepted_risks,
                stale_reasons=entry.stale_reasons,
                last_sequence=entry.last_sequence,
            )
            for entry in summary.entries
        ],
        safe_next_actions=summary.safe_next_actions,
        non_claims=summary.non_claims,
    )


def build_verification_plan_entry_response(entry) -> VerificationPlanEntryResponse:
    return VerificationPlanEntryResponse(
        verification_id=str(entry.verification_id),
        check_name=entry.check_name,
        kind=entry.kind.value,
        lifecycle_state=entry.lifecycle_state.value,
        target=(
            VerificationPlanTargetResponse(
                kind=entry.target.kind.value,
                target_id=entry.target.target_id,
                label=entry.target.label,
            )
            if entry.target is not None
            else None
        ),
        command=entry.command,
        command_recipe=(
            VerificationPlanCommandRecipeResponse(
                command=entry.command_recipe.command,
                display=entry.command_recipe.display,
                purpose=entry.command_recipe.purpose,
                safety_class=entry.command_recipe.safety_class.value,
                requires_approval=entry.command_recipe.requires_approval,
                expected_exit_codes=entry.command_recipe.expected_exit_codes,
                timeout_seconds=entry.command_recipe.timeout_seconds,
                cwd_hint=entry.command_recipe.cwd_hint,
            )
            if entry.command_recipe is not None
            else None
        ),
        source=entry.source.value,
        rationale=entry.rationale,
        selection_rationale=entry.selection_rationale,
        blocking=entry.blocking,
        timeout_seconds=entry.timeout_seconds,
        expected_exit_codes=entry.expected_exit_codes,
        changed_paths=[path.as_posix() for path in entry.changed_paths],
        eval_case_id=entry.eval_case_id,
        eval_profile_id=entry.eval_profile_id,
        release_surfaces=entry.release_surfaces,
        evidence_references=[
            VerificationPlanEvidenceRefResponse(
                kind=ref.kind.value,
                ref_id=ref.ref_id,
                summary=ref.summary,
                source_path=ref.source_path,
                freshness=ref.freshness,
                redaction=ref.redaction,
                reviewer_safe=ref.reviewer_safe,
            )
            for ref in entry.evidence_references
        ],
        stale_reasons=entry.stale_reasons,
        manual_evidence_required=entry.manual_evidence_required,
        execution_requires_approval=entry.execution_requires_approval,
        superseded_by_verification_id=_optional_str(
            entry.superseded_by_verification_id
        ),
    )


def build_verification_review_loop_summary_response(
    summary,
) -> ChangesetVerificationReviewLoopSummaryResponse:
    return ChangesetVerificationReviewLoopSummaryResponse(
        feedback_count=summary.feedback_count,
        open_feedback_count=summary.open_feedback_count,
        response_state_counts=summary.response_state_counts,
        stale_response_count=summary.stale_response_count,
        missing_response_verification_count=summary.missing_response_verification_count,
        failed_response_verification_count=summary.failed_response_verification_count,
        accepted_risk_response_count=summary.accepted_risk_response_count,
        manual_evidence_count=summary.manual_evidence_count,
        manual_evidence_kind_counts=summary.manual_evidence_kind_counts,
        browser_evidence_count=summary.browser_evidence_count,
        accessibility_evidence_count=summary.accessibility_evidence_count,
        skipped_live_evidence_count=summary.skipped_live_evidence_count,
        skipped_browser_evidence_count=summary.skipped_browser_evidence_count,
        skipped_accessibility_evidence_count=(
            summary.skipped_accessibility_evidence_count
        ),
        stale_check_count=summary.stale_check_count,
        topology_impact_count=summary.topology_impact_count,
        retained_verification_state=summary.retained_verification_state.value,
        safe_next_actions=summary.safe_next_actions,
        limitations=summary.limitations,
        non_claims=summary.non_claims,
    )


def build_changeset_verification_readiness_response(
    readiness,
) -> ChangesetVerificationReadinessResponse:
    return ChangesetVerificationReadinessResponse(
        state=readiness.state.value,
        summary=readiness.summary,
        requirements=[
            ChangesetVerificationRequirementResponse(
                requirement_id=requirement.requirement_id,
                state=requirement.state.value,
                check_name=requirement.check_name,
                reason=requirement.reason,
                source=(
                    requirement.source.value if requirement.source is not None else None
                ),
                kind=requirement.kind.value if requirement.kind is not None else None,
                command=requirement.command,
                changed_paths=requirement.changed_paths,
                verification_id=_optional_str(requirement.verification_id),
                artifact_id=_optional_str(requirement.artifact_id),
                blocking=requirement.blocking,
                evidence_summary=requirement.evidence_summary,
                safe_next_actions=requirement.safe_next_actions,
            )
            for requirement in readiness.requirements
        ],
        stale_count=readiness.stale_count,
        missing_count=readiness.missing_count,
        failed_count=readiness.failed_count,
        accepted_risk_count=readiness.accepted_risk_count,
        safe_next_actions=readiness.safe_next_actions,
        non_claims=readiness.non_claims,
    )


def build_changeset_review_brief_generate_response(
    result: ChangesetReviewBriefGenerationResult,
    detail: ChangesetDetailView,
    *,
    include_markdown: bool = False,
) -> ChangesetReviewBriefGenerateResponse:
    return ChangesetReviewBriefGenerateResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        artifact_id=str(result.artifact.artifact_id),
        artifact_path=result.artifact.relative_path.as_posix(),
        event_sequence=result.event.sequence,
        readiness_event_sequence=result.readiness_event.sequence,
        brief=result.brief.model_dump(mode="json"),
        markdown=result.markdown if include_markdown else None,
        limitations=result.limitations,
        limitation_summary=(
            result.limitation_summary.model_dump(mode="json")
            if result.limitation_summary is not None
            else None
        ),
        detail=build_changeset_detail_response(detail),
    )


def build_changeset_source_response(
    source: ChangesetSourceRecord,
) -> ChangesetSourceResponse:
    return ChangesetSourceResponse(
        session_id=str(source.session_id),
        changeset_id=str(source.changeset_id),
        source_kind=source.source_kind.value,
        source_session_id=_optional_str(source.source_session_id),
        task_id=_optional_str(source.task_id),
        turn_id=_optional_str(source.turn_id),
        branch_search_id=_optional_str(source.branch_search_id),
        branch_candidate_id=_optional_str(source.branch_candidate_id),
        verification_id=_optional_str(source.verification_id),
        artifact_id=_optional_str(source.artifact_id),
        reason=source.reason,
        limitation=source.limitation,
        created_at=source.created_at,
        last_sequence=source.last_sequence,
    )


def build_changeset_inventory_response(
    inventory: ChangesetInventoryRecord,
) -> ChangesetInventoryResponse:
    return ChangesetInventoryResponse(
        session_id=str(inventory.session_id),
        changeset_id=str(inventory.changeset_id),
        artifact_id=str(inventory.artifact_id),
        artifact_schema_version=inventory.artifact_schema_version,
        freshness=inventory.freshness.value,
        changed_path_count=inventory.changed_path_count,
        source_digest=inventory.source_digest,
        previous_artifact_id=_optional_str(inventory.previous_artifact_id),
        refreshed_by=inventory.refreshed_by,
        task_id=_optional_str(inventory.task_id),
        turn_id=_optional_str(inventory.turn_id),
        branch_search_id=_optional_str(inventory.branch_search_id),
        branch_candidate_id=_optional_str(inventory.branch_candidate_id),
        risk_level=inventory.risk_level.value,
        risk_summary=inventory.risk_summary,
        unresolved_risk_count=inventory.unresolved_risk_count,
        accepted_risk_count=inventory.accepted_risk_count,
        updated_at=inventory.updated_at,
        last_sequence=inventory.last_sequence,
    )


def build_changeset_verification_posture_response(
    posture: ChangesetVerificationPostureRecord,
) -> ChangesetVerificationPostureResponse:
    return ChangesetVerificationPostureResponse(
        session_id=str(posture.session_id),
        changeset_id=str(posture.changeset_id),
        state=posture.state.value,
        summary=posture.summary,
        verification_id=_optional_str(posture.verification_id),
        artifact_id=_optional_str(posture.artifact_id),
        task_id=_optional_str(posture.task_id),
        turn_id=_optional_str(posture.turn_id),
        stale_count=posture.stale_count,
        missing_count=posture.missing_count,
        failed_count=posture.failed_count,
        accepted_risk_count=posture.accepted_risk_count,
        updated_at=posture.updated_at,
        last_sequence=posture.last_sequence,
    )


def build_changeset_review_brief_response(
    brief: ChangesetReviewBriefRecord,
) -> ChangesetReviewBriefResponse:
    return ChangesetReviewBriefResponse(
        session_id=str(brief.session_id),
        changeset_id=str(brief.changeset_id),
        artifact_id=str(brief.artifact_id),
        artifact_schema_version=brief.artifact_schema_version,
        render_targets=brief.render_targets,
        inventory_artifact_id=_optional_str(brief.inventory_artifact_id),
        verification_id=_optional_str(brief.verification_id),
        task_id=_optional_str(brief.task_id),
        turn_id=_optional_str(brief.turn_id),
        created_by=brief.created_by,
        redacted=brief.redacted,
        local_only=brief.local_only,
        created_at=brief.created_at,
        last_sequence=brief.last_sequence,
    )


def build_changeset_readiness_response(
    readiness: ChangesetReadinessRecord,
) -> ChangesetReadinessResponse:
    return ChangesetReadinessResponse(
        session_id=str(readiness.session_id),
        changeset_id=str(readiness.changeset_id),
        readiness_kind=readiness.readiness_kind.value,
        state=readiness.state.value,
        reason=readiness.reason,
        blockers=readiness.blockers,
        safe_next_actions=readiness.safe_next_actions,
        inventory_artifact_id=_optional_str(readiness.inventory_artifact_id),
        review_brief_artifact_id=_optional_str(readiness.review_brief_artifact_id),
        verification_id=_optional_str(readiness.verification_id),
        task_id=_optional_str(readiness.task_id),
        turn_id=_optional_str(readiness.turn_id),
        accepted_risk_count=readiness.accepted_risk_count,
        decided_by=readiness.decided_by,
        updated_at=readiness.updated_at,
        last_sequence=readiness.last_sequence,
    )


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


__all__ = (
    "build_changeset_summary_response",
    "build_changeset_summary_responses",
    "build_changeset_detail_response",
    "build_changeset_verification_plan_response",
    "build_verification_review_loop_summary_response",
    "build_changeset_verification_readiness_response",
    "build_changeset_review_brief_generate_response",
    "build_changeset_source_response",
    "build_changeset_inventory_response",
    "build_changeset_verification_posture_response",
    "build_changeset_review_brief_response",
    "build_changeset_readiness_response",
    "_optional_str",
)
