"""Commit and handoff readiness response builders."""

from glassbox.runtime.commit_messages import CommitMessageSuggestion
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.handoff_readiness import HandoffReadinessAssessment
from glassbox.web.changeset_api_builders_detail import (
    build_changeset_verification_plan_summary_response,
)
from glassbox.web.changeset_api_models import CommitMessageEvidenceLineResponse
from glassbox.web.changeset_api_models import CommitMessageSuggestionResponse
from glassbox.web.changeset_api_models import CommitReadinessGitSummaryResponse
from glassbox.web.changeset_api_models import CommitReadinessResponse
from glassbox.web.changeset_api_models import CommitReadinessSignalResponse
from glassbox.web.changeset_api_models import HandoffReadinessEvidenceSummaryResponse
from glassbox.web.changeset_api_models import HandoffReadinessResponse
from glassbox.web.changeset_api_models import HandoffReadinessSignalResponse


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
        verification_plan_summary=build_changeset_verification_plan_summary_response(
            readiness.verification_plan_summary
        ),
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
            skipped_live_evidence_count=(
                readiness.evidence.skipped_live_evidence_count
            ),
            skipped_browser_evidence_count=(
                readiness.evidence.skipped_browser_evidence_count
            ),
            skipped_accessibility_evidence_count=(
                readiness.evidence.skipped_accessibility_evidence_count
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


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


__all__ = (
    "build_commit_message_suggestion_response",
    "build_commit_readiness_response",
    "build_handoff_readiness_response",
    "_optional_str",
)
