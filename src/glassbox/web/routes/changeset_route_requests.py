"""Request coercion helpers for changeset routes."""

from uuid import UUID

from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.web.changeset_api import AccessibilityEvidenceAttachRequest
from glassbox.web.changeset_api import BrowserEvidenceAttachRequest
from glassbox.web.changeset_api import ChangesetCreateRequest
from glassbox.web.changeset_api import ChangesetRecordVerificationRequest
from glassbox.web.changeset_api import ManualEvidenceAttachRequest
from glassbox.web.changeset_api import ReviewFeedbackCreateRequest
from glassbox.web.routes.changeset_route_services import workspace_root_for_session


def optional_uuid(value: str | None) -> UUID | None:
    return UUID(value) if value is not None else None


def review_feedback_disposition(
    value: str | None,
) -> ReviewFeedbackDisposition | None:
    return ReviewFeedbackDisposition(value) if value is not None else None


def manual_evidence_state(value: str | None) -> ManualEvidenceState | None:
    return ManualEvidenceState(value) if value is not None else None


def review_feedback_kind(request: ReviewFeedbackCreateRequest) -> ReviewFeedbackKind:
    return ReviewFeedbackKind(request.feedback_kind)


def review_feedback_provenance(
    request: ReviewFeedbackCreateRequest,
) -> ReviewFeedbackProvenance:
    return ReviewFeedbackProvenance(request.provenance)


def review_feedback_scope_kind(
    request: ReviewFeedbackCreateRequest,
) -> ReviewFeedbackScopeKind:
    return ReviewFeedbackScopeKind(request.scope_kind)


def manual_evidence_kind(request: ManualEvidenceAttachRequest) -> ManualEvidenceKind:
    return ManualEvidenceKind(request.evidence_kind)


def manual_evidence_target_kind(
    request: (
        AccessibilityEvidenceAttachRequest
        | BrowserEvidenceAttachRequest
        | ManualEvidenceAttachRequest
    ),
) -> ManualEvidenceTargetKind:
    return ManualEvidenceTargetKind(request.target_kind)


def manual_evidence_freshness(
    request: (
        AccessibilityEvidenceAttachRequest
        | BrowserEvidenceAttachRequest
        | ManualEvidenceAttachRequest
    ),
) -> ManualEvidenceFreshness:
    return ManualEvidenceFreshness(request.freshness)


def record_verification_task_id(
    request: ChangesetRecordVerificationRequest,
) -> UUID | None:
    return optional_uuid(request.task_id)


def record_verification_id(
    request: ChangesetRecordVerificationRequest,
) -> UUID | None:
    return optional_uuid(request.verification_id)


def create_changeset_from_request(
    request: ChangesetCreateRequest,
    *,
    repository: ChangesetRepository,
    service: ChangesetDerivationService,
) -> ChangesetDerivationResult:
    if request.source_kind == "session":
        if request.session_id is None:
            raise ValueError("session_id is required for source_kind=session")
        return service.create_from_session(
            UUID(request.session_id),
            objective=request.objective,
        )
    if request.source_kind == "task":
        if request.task_id is None:
            raise ValueError("task_id is required for source_kind=task")
        return service.create_from_task(
            UUID(request.task_id),
            objective=request.objective,
        )
    if request.source_kind == "branch-candidate":
        if request.branch_search_id is None or request.candidate_id is None:
            raise ValueError(
                "branch_search_id and candidate_id are required for "
                "source_kind=branch-candidate"
            )
        return service.create_from_branch_candidate(
            UUID(request.branch_search_id),
            UUID(request.candidate_id),
            objective=request.objective,
        )
    if request.session_id is None:
        raise ValueError("session_id is required for source_kind=workspace-diff")
    session_id = UUID(request.session_id)
    return service.create_from_workspace_diff(
        session_id,
        workspace_root_for_session(
            repository=repository,
            session_id=session_id,
        ),
        objective=request.objective,
    )


__all__ = [
    "create_changeset_from_request",
    "manual_evidence_freshness",
    "manual_evidence_kind",
    "manual_evidence_state",
    "manual_evidence_target_kind",
    "optional_uuid",
    "record_verification_id",
    "record_verification_task_id",
    "review_feedback_disposition",
    "review_feedback_kind",
    "review_feedback_provenance",
    "review_feedback_scope_kind",
]
