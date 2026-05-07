"""Response builders for changeset HTTP transport models."""

from collections.abc import Sequence

from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord
from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ManualEvidenceRecordResult
from glassbox.runtime.changesets import ReviewFeedbackRecordResult
from glassbox.runtime.commit_messages import CommitMessageSuggestion
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.handoff_readiness import HandoffReadinessAssessment
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus
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
from glassbox.web.changeset_api_models import ChangesetVerificationPlanPreviewResponse
from glassbox.web.changeset_api_models import ChangesetVerificationPostureResponse
from glassbox.web.changeset_api_models import ChangesetVerificationReadinessResponse
from glassbox.web.changeset_api_models import ChangesetVerificationReasonGroupResponse
from glassbox.web.changeset_api_models import ChangesetVerificationRecipePreviewResponse
from glassbox.web.changeset_api_models import ChangesetVerificationRequirementResponse
from glassbox.web.changeset_api_models import (
    ChangesetVerificationReviewLoopSummaryResponse,
)
from glassbox.web.changeset_api_models import CommitMessageEvidenceLineResponse
from glassbox.web.changeset_api_models import CommitMessageSuggestionResponse
from glassbox.web.changeset_api_models import CommitReadinessGitSummaryResponse
from glassbox.web.changeset_api_models import CommitReadinessResponse
from glassbox.web.changeset_api_models import CommitReadinessSignalResponse
from glassbox.web.changeset_api_models import HandoffReadinessEvidenceSummaryResponse
from glassbox.web.changeset_api_models import HandoffReadinessResponse
from glassbox.web.changeset_api_models import HandoffReadinessSignalResponse
from glassbox.web.review_loop_api import ChangesetReviewResponseSummaryResponse
from glassbox.web.review_loop_api import ManualEvidenceActionResponse
from glassbox.web.review_loop_api import ManualEvidenceResponse
from glassbox.web.review_loop_api import ReviewFeedbackActionResponse
from glassbox.web.review_loop_api import ReviewFeedbackDetailResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponseStatusResponse
from glassbox.web.review_loop_api import ReviewFeedbackScopeResponse


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
        limitations=preview.limitations,
        safe_next_actions=preview.safe_next_actions,
        non_claims=preview.non_claims,
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


def build_commit_message_suggestion_response(
    suggestion: CommitMessageSuggestion,
) -> CommitMessageSuggestionResponse:
    return CommitMessageSuggestionResponse(
        suggestion_kind=suggestion.suggestion_kind,
        schema_version=suggestion.schema_version,
        suggestion_label=suggestion.suggestion_label,
        changeset_id=str(suggestion.changeset_id),
        session_id=str(suggestion.session_id),
        style=suggestion.style,
        subject=suggestion.subject,
        body=suggestion.body,
        message=suggestion.message,
        deterministic=suggestion.deterministic,
        commit_readiness_state=suggestion.commit_readiness_state,
        evidence=[
            CommitMessageEvidenceLineResponse(
                kind=line.kind,
                summary=line.summary,
                references=line.references,
            )
            for line in suggestion.evidence
        ],
        limitations=suggestion.limitations,
        non_claims=suggestion.non_claims,
    )


def build_commit_readiness_response(
    readiness: CommitReadinessAssessment,
) -> CommitReadinessResponse:
    return CommitReadinessResponse(
        changeset_id=str(readiness.changeset_id),
        session_id=str(readiness.session_id),
        readiness_kind=readiness.readiness_kind.value,
        state=readiness.state.value,
        reason=readiness.reason,
        blockers=readiness.blockers,
        safe_next_actions=readiness.safe_next_actions,
        inventory_artifact_id=_optional_str(readiness.inventory_artifact_id),
        review_brief_artifact_id=_optional_str(readiness.review_brief_artifact_id),
        verification_id=_optional_str(readiness.verification_id),
        review_feedback_count=readiness.review_feedback_count,
        unresolved_feedback_count=readiness.unresolved_feedback_count,
        stale_response_count=readiness.stale_response_count,
        manual_evidence_count=readiness.manual_evidence_count,
        local_only_evidence_count=readiness.local_only_evidence_count,
        accepted_risk_count=readiness.accepted_risk_count,
        git=CommitReadinessGitSummaryResponse(
            branch=readiness.git.branch,
            ahead=readiness.git.ahead,
            behind=readiness.git.behind,
            staged_paths=readiness.git.staged_paths,
            unstaged_paths=readiness.git.unstaged_paths,
            untracked_paths=readiness.git.untracked_paths,
            workspace_path_count=readiness.git.workspace_path_count,
            staged_path_count=readiness.git.staged_path_count,
            policy_sensitive_paths=readiness.git.policy_sensitive_paths,
            generated_paths=readiness.git.generated_paths,
            clean=readiness.git.clean,
            error=readiness.git.error,
        ),
        signals=[
            CommitReadinessSignalResponse(
                signal_id=signal.signal_id,
                state=signal.state.value,
                summary=signal.summary,
                blocking=signal.blocking,
                paths=signal.paths,
            )
            for signal in readiness.signals
        ],
        non_claims=readiness.non_claims,
    )


def build_handoff_readiness_response(
    readiness: HandoffReadinessAssessment,
) -> HandoffReadinessResponse:
    return HandoffReadinessResponse(
        changeset_id=str(readiness.changeset_id),
        session_id=str(readiness.session_id),
        readiness_kind=readiness.readiness_kind,
        state=readiness.state,
        reason=readiness.reason,
        blockers=readiness.blockers,
        limitations=readiness.limitations,
        safe_next_actions=readiness.safe_next_actions,
        inventory_artifact_id=_optional_str(readiness.inventory_artifact_id),
        review_brief_artifact_id=_optional_str(readiness.review_brief_artifact_id),
        verification_id=_optional_str(readiness.verification_id),
        commit_readiness_state=readiness.commit_readiness_state.value,
        evidence=HandoffReadinessEvidenceSummaryResponse(
            feedback_count=readiness.evidence.feedback_count,
            unresolved_feedback_count=(readiness.evidence.unresolved_feedback_count),
            stale_response_count=readiness.evidence.stale_response_count,
            manual_evidence_count=readiness.evidence.manual_evidence_count,
            local_only_evidence_count=readiness.evidence.local_only_evidence_count,
            stale_manual_evidence_count=(
                readiness.evidence.stale_manual_evidence_count
            ),
            needs_inspection_evidence_count=(
                readiness.evidence.needs_inspection_evidence_count
            ),
            browser_evidence_count=readiness.evidence.browser_evidence_count,
            accessibility_evidence_count=(
                readiness.evidence.accessibility_evidence_count
            ),
            review_brief_count=readiness.evidence.review_brief_count,
            accepted_risk_count=readiness.evidence.accepted_risk_count,
        ),
        git=CommitReadinessGitSummaryResponse(
            branch=readiness.git.branch,
            ahead=readiness.git.ahead,
            behind=readiness.git.behind,
            staged_paths=readiness.git.staged_paths,
            unstaged_paths=readiness.git.unstaged_paths,
            untracked_paths=readiness.git.untracked_paths,
            workspace_path_count=readiness.git.workspace_path_count,
            staged_path_count=readiness.git.staged_path_count,
            policy_sensitive_paths=readiness.git.policy_sensitive_paths,
            generated_paths=readiness.git.generated_paths,
            clean=readiness.git.clean,
            error=readiness.git.error,
        ),
        signals=[
            HandoffReadinessSignalResponse(
                signal_id=signal.signal_id,
                state=signal.state,
                summary=signal.summary,
                blocking=signal.blocking,
                paths=signal.paths,
            )
            for signal in readiness.signals
        ],
        non_claims=readiness.non_claims,
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


def build_review_feedback_response(
    feedback: ReviewFeedbackRecord,
) -> ReviewFeedbackResponse:
    return ReviewFeedbackResponse(
        session_id=str(feedback.session_id),
        feedback_id=str(feedback.feedback_id),
        changeset_id=str(feedback.changeset_id),
        feedback_kind=feedback.feedback_kind.value,
        provenance=feedback.provenance.value,
        disposition=feedback.disposition.value,
        summary=feedback.summary,
        body=feedback.body,
        source_label=feedback.source_label,
        reviewer_label=feedback.reviewer_label,
        created_by=feedback.created_by,
        updated_by=feedback.updated_by,
        resolved_by=feedback.resolved_by,
        archived_by=feedback.archived_by,
        accepted_by=feedback.accepted_by,
        source_session_id=_optional_str(feedback.source_session_id),
        task_id=_optional_str(feedback.task_id),
        turn_id=_optional_str(feedback.turn_id),
        artifact_id=_optional_str(feedback.artifact_id),
        verification_id=_optional_str(feedback.verification_id),
        resolution_summary=feedback.resolution_summary,
        residual_risk=feedback.residual_risk,
        risk_summary=feedback.risk_summary,
        acceptance_reason=feedback.acceptance_reason,
        archived_reason=feedback.archived_reason,
        replacement_feedback_id=_optional_str(feedback.replacement_feedback_id),
        reopened_count=feedback.reopened_count,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        last_sequence=feedback.last_sequence,
    )


def build_manual_evidence_response(
    evidence: ManualEvidenceRecord,
) -> ManualEvidenceResponse:
    return ManualEvidenceResponse(
        session_id=str(evidence.session_id),
        evidence_id=str(evidence.evidence_id),
        evidence_kind=evidence.evidence_kind.value,
        state=evidence.state.value,
        target_kind=evidence.target_kind.value,
        target_id=evidence.target_id,
        changeset_id=_optional_str(evidence.changeset_id),
        feedback_id=_optional_str(evidence.feedback_id),
        artifact_id=_optional_str(evidence.artifact_id),
        artifact_schema_version=evidence.artifact_schema_version,
        summary=evidence.summary,
        source_label=evidence.source_label,
        observed_at=evidence.observed_at,
        created_by=evidence.created_by,
        local_only=evidence.local_only,
        redaction_status=evidence.redaction_status.value,
        freshness=evidence.freshness.value,
        limitations=evidence.limitations,
        non_claims=evidence.non_claims,
        rejected_reason=evidence.rejected_reason,
        archived_reason=evidence.archived_reason,
        superseded_reason=evidence.superseded_reason,
        replacement_evidence_id=_optional_str(evidence.replacement_evidence_id),
        task_id=_optional_str(evidence.task_id),
        turn_id=_optional_str(evidence.turn_id),
        verification_id=_optional_str(evidence.verification_id),
        created_at=evidence.created_at,
        updated_at=evidence.updated_at,
        last_sequence=evidence.last_sequence,
    )


def build_manual_evidence_action_response(
    result: ManualEvidenceRecordResult,
) -> ManualEvidenceActionResponse:
    return ManualEvidenceActionResponse(
        evidence=build_manual_evidence_response(result.evidence),
        artifact_id=(
            str(result.artifact.artifact_id) if result.artifact is not None else None
        ),
        artifact_path=(
            result.artifact.relative_path.as_posix()
            if result.artifact is not None
            else None
        ),
        event_sequence=result.event.sequence,
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
    )


def build_review_feedback_scope_response(
    scope: ReviewFeedbackScopeRecord,
) -> ReviewFeedbackScopeResponse:
    return ReviewFeedbackScopeResponse(
        session_id=str(scope.session_id),
        feedback_id=str(scope.feedback_id),
        changeset_id=str(scope.changeset_id),
        scope_kind=scope.scope_kind.value,
        reason=scope.reason,
        source_session_id=_optional_str(scope.source_session_id),
        task_id=_optional_str(scope.task_id),
        turn_id=_optional_str(scope.turn_id),
        artifact_id=_optional_str(scope.artifact_id),
        verification_id=_optional_str(scope.verification_id),
        branch_search_id=_optional_str(scope.branch_search_id),
        branch_candidate_id=_optional_str(scope.branch_candidate_id),
        file_path=scope.file_path,
        line_start=scope.line_start,
        line_end=scope.line_end,
        created_at=scope.created_at,
        last_sequence=scope.last_sequence,
    )


def build_review_feedback_response_status_response(
    status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackResponseStatusResponse:
    return ReviewFeedbackResponseStatusResponse(
        feedback_id=str(status.feedback_id),
        changeset_id=str(status.changeset_id),
        response_state=status.response_state.value,
        disposition=status.disposition.value,
        summary=status.summary,
        fixup_inventory_count=status.fixup_inventory_count,
        latest_fixup_inventory_artifact_id=_optional_str(
            status.latest_fixup_inventory_artifact_id
        ),
        latest_fixup_inventory_sequence=status.latest_fixup_inventory_sequence,
        latest_fixup_inventory_at=status.latest_fixup_inventory_at,
        latest_source_kind=(
            status.latest_source_kind.value
            if status.latest_source_kind is not None
            else None
        ),
        latest_source_summary=status.latest_source_summary,
        inventory_freshness=status.inventory_freshness.value,
        stale=status.stale,
        stale_reason=status.stale_reason,
        changed_path_count=status.changed_path_count,
        matched_scope_path_count=status.matched_scope_path_count,
        path_summaries=status.path_summaries,
        verification_state=status.verification_state.value,
        verification_reason=status.verification_reason,
        verification_requirement_ids=status.verification_requirement_ids,
        verification_safe_next_actions=status.verification_safe_next_actions,
        blockers=status.blockers,
        safe_next_actions=status.safe_next_actions,
        non_claims=status.non_claims,
    )


def build_review_response_summary_response(
    summary: ChangesetReviewResponseSummary,
) -> ChangesetReviewResponseSummaryResponse:
    return ChangesetReviewResponseSummaryResponse(
        changeset_id=str(summary.changeset_id),
        total_feedback_count=summary.total_feedback_count,
        open_count=summary.open_count,
        responded_count=summary.responded_count,
        unresolved_count=summary.unresolved_count,
        stale_response_count=summary.stale_response_count,
        accepted_risk_count=summary.accepted_risk_count,
        blocked_count=summary.blocked_count,
        items=[
            build_review_feedback_response_status_response(item)
            for item in summary.items
        ],
        blockers=summary.blockers,
        safe_next_actions=summary.safe_next_actions,
        non_claims=summary.non_claims,
    )


def build_review_feedback_detail_response(
    feedback: ReviewFeedbackRecord,
    scopes: Sequence[ReviewFeedbackScopeRecord],
    response_status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackDetailResponse:
    return ReviewFeedbackDetailResponse(
        feedback=build_review_feedback_response(feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in scopes],
        response_status=build_review_feedback_response_status_response(response_status),
        safe_next_actions=[
            f"glassbox changeset feedback show {feedback.feedback_id} --cwd .",
            f"glassbox changeset show {feedback.changeset_id} --cwd .",
        ],
        non_claims=_review_feedback_non_claims(),
    )


def build_review_feedback_action_response(
    result: ReviewFeedbackRecordResult,
) -> ReviewFeedbackActionResponse:
    return ReviewFeedbackActionResponse(
        feedback=build_review_feedback_response(result.feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in result.scopes],
        event_sequences=[event.sequence for event in result.events],
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
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


def _review_feedback_non_claims() -> list[str]:
    return [
        "review feedback is local evidence, not approval",
        "Glassbox did not stage, commit, push, open a PR, or merge",
    ]


__all__ = (
    "build_changeset_summary_response",
    "build_changeset_summary_responses",
    "build_changeset_detail_response",
    "build_changeset_verification_plan_response",
    "build_verification_review_loop_summary_response",
    "build_changeset_verification_readiness_response",
    "build_changeset_review_brief_generate_response",
    "build_commit_message_suggestion_response",
    "build_commit_readiness_response",
    "build_handoff_readiness_response",
    "build_changeset_source_response",
    "build_changeset_inventory_response",
    "build_changeset_verification_posture_response",
    "build_changeset_review_brief_response",
    "build_review_feedback_response",
    "build_manual_evidence_response",
    "build_manual_evidence_action_response",
    "build_review_feedback_scope_response",
    "build_review_feedback_response_status_response",
    "build_review_response_summary_response",
    "build_review_feedback_detail_response",
    "build_review_feedback_action_response",
    "build_changeset_readiness_response",
    "_optional_str",
    "_review_feedback_non_claims",
)
