"""Compatibility facade for changeset HTTP transport models and builders."""

from glassbox.web.changeset_api_builders import _optional_str
from glassbox.web.changeset_api_builders import _review_feedback_non_claims
from glassbox.web.changeset_api_builders import build_changeset_detail_response
from glassbox.web.changeset_api_builders import build_changeset_inventory_response
from glassbox.web.changeset_api_builders import build_changeset_readiness_response
from glassbox.web.changeset_api_builders import (
    build_changeset_review_brief_generate_response,
)
from glassbox.web.changeset_api_builders import build_changeset_review_brief_response
from glassbox.web.changeset_api_builders import build_changeset_source_response
from glassbox.web.changeset_api_builders import build_changeset_summary_response
from glassbox.web.changeset_api_builders import build_changeset_summary_responses
from glassbox.web.changeset_api_builders import (
    build_changeset_verification_plan_response,
)
from glassbox.web.changeset_api_builders import (
    build_changeset_verification_posture_response,
)
from glassbox.web.changeset_api_builders import (
    build_changeset_verification_readiness_response,
)
from glassbox.web.changeset_api_builders import build_commit_message_suggestion_response
from glassbox.web.changeset_api_builders import build_commit_readiness_response
from glassbox.web.changeset_api_builders import build_handoff_readiness_response
from glassbox.web.changeset_api_builders import build_manual_evidence_action_response
from glassbox.web.changeset_api_builders import build_manual_evidence_response
from glassbox.web.changeset_api_builders import build_review_feedback_action_response
from glassbox.web.changeset_api_builders import build_review_feedback_detail_response
from glassbox.web.changeset_api_builders import build_review_feedback_response
from glassbox.web.changeset_api_builders import (
    build_review_feedback_response_status_response,
)
from glassbox.web.changeset_api_builders import build_review_feedback_scope_response
from glassbox.web.changeset_api_builders import build_review_response_summary_response
from glassbox.web.changeset_api_builders import (
    build_verification_review_loop_summary_response,
)
from glassbox.web.changeset_api_models import ChangesetActionResponse
from glassbox.web.changeset_api_models import ChangesetArchiveRequest
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceItemResponse
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceSummaryResponse
from glassbox.web.changeset_api_models import ChangesetCreateRequest
from glassbox.web.changeset_api_models import ChangesetCreateResponse
from glassbox.web.changeset_api_models import ChangesetDetailResponse
from glassbox.web.changeset_api_models import ChangesetInventoryResponse
from glassbox.web.changeset_api_models import ChangesetInventoryStatusResponse
from glassbox.web.changeset_api_models import ChangesetListPageResponse
from glassbox.web.changeset_api_models import ChangesetReadinessResponse
from glassbox.web.changeset_api_models import ChangesetRecordVerificationRequest
from glassbox.web.changeset_api_models import ChangesetRecordVerificationResponse
from glassbox.web.changeset_api_models import ChangesetRefreshRequest
from glassbox.web.changeset_api_models import ChangesetReviewBriefGenerateResponse
from glassbox.web.changeset_api_models import ChangesetReviewBriefRequest
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
from glassbox.web.review_loop_api import AccessibilityEvidenceAttachRequest
from glassbox.web.review_loop_api import BrowserEvidenceAttachRequest
from glassbox.web.review_loop_api import ChangesetReviewResponseSummaryResponse
from glassbox.web.review_loop_api import ManualEvidenceActionResponse
from glassbox.web.review_loop_api import ManualEvidenceAttachRequest
from glassbox.web.review_loop_api import ManualEvidenceListPageResponse
from glassbox.web.review_loop_api import ManualEvidenceResponse
from glassbox.web.review_loop_api import ReviewFeedbackAcceptRiskRequest
from glassbox.web.review_loop_api import ReviewFeedbackActionResponse
from glassbox.web.review_loop_api import ReviewFeedbackArchiveRequest
from glassbox.web.review_loop_api import ReviewFeedbackCreateRequest
from glassbox.web.review_loop_api import ReviewFeedbackDetailResponse
from glassbox.web.review_loop_api import ReviewFeedbackListPageResponse
from glassbox.web.review_loop_api import ReviewFeedbackReopenRequest
from glassbox.web.review_loop_api import ReviewFeedbackResolveRequest
from glassbox.web.review_loop_api import ReviewFeedbackResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponseStatusResponse
from glassbox.web.review_loop_api import ReviewFeedbackScopeResponse

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
    "ChangesetSummaryResponse",
    "ChangesetSourceResponse",
    "ChangesetInventoryResponse",
    "ChangesetInventoryStatusResponse",
    "ChangesetCommandEvidenceItemResponse",
    "ChangesetCommandEvidenceSummaryResponse",
    "ChangesetVerificationPostureResponse",
    "ChangesetReviewBriefResponse",
    "ChangesetReadinessResponse",
    "ChangesetListPageResponse",
    "ChangesetDetailResponse",
    "ChangesetCreateRequest",
    "ChangesetCreateResponse",
    "ChangesetArchiveRequest",
    "ChangesetRefreshRequest",
    "ChangesetActionResponse",
    "ChangesetVerificationRecipePreviewResponse",
    "ChangesetTopologyImpactResponse",
    "ChangesetVerificationReasonGroupResponse",
    "ChangesetVerificationRequirementResponse",
    "ChangesetVerificationReadinessResponse",
    "ChangesetVerificationReviewLoopSummaryResponse",
    "ChangesetVerificationPlanPreviewResponse",
    "ChangesetRecordVerificationRequest",
    "ChangesetRecordVerificationResponse",
    "ChangesetReviewBriefRequest",
    "ChangesetReviewBriefGenerateResponse",
    "CommitMessageEvidenceLineResponse",
    "CommitMessageSuggestionResponse",
    "CommitReadinessSignalResponse",
    "CommitReadinessGitSummaryResponse",
    "CommitReadinessResponse",
    "HandoffReadinessSignalResponse",
    "HandoffReadinessEvidenceSummaryResponse",
    "HandoffReadinessResponse",
    "ReviewFeedbackScopeResponse",
    "ReviewFeedbackResponse",
    "ReviewFeedbackResponseStatusResponse",
    "ChangesetReviewResponseSummaryResponse",
    "ManualEvidenceResponse",
    "ReviewFeedbackCreateRequest",
    "ManualEvidenceAttachRequest",
    "BrowserEvidenceAttachRequest",
    "AccessibilityEvidenceAttachRequest",
    "ManualEvidenceListPageResponse",
    "ManualEvidenceActionResponse",
    "ReviewFeedbackResolveRequest",
    "ReviewFeedbackReopenRequest",
    "ReviewFeedbackArchiveRequest",
    "ReviewFeedbackAcceptRiskRequest",
    "ReviewFeedbackListPageResponse",
    "ReviewFeedbackDetailResponse",
    "ReviewFeedbackActionResponse",
)
