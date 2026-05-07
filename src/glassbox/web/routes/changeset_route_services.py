"""Service wiring helpers for changeset routes."""

from pathlib import Path
from typing import cast
from uuid import UUID

from glassbox.runtime.changesets import AccessibilityEvidenceActionService
from glassbox.runtime.changesets import BrowserEvidenceActionService
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.changesets import ManualEvidenceActionService
from glassbox.runtime.changesets import ReviewFeedbackActionService
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryService
from glassbox.runtime.commit_messages import ChangesetCommitMessageSuggestionService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService


def changeset_repository(context: RuntimeContext) -> ChangesetRepository:
    return cast(ChangesetRepository, context.repositories.sessions)


def changeset_query_service(repository: ChangesetRepository) -> ChangesetQueryService:
    return ChangesetQueryService(repository)


def changeset_derivation_service(
    repository: ChangesetRepository,
) -> ChangesetDerivationService:
    return ChangesetDerivationService(repository)


def changeset_action_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetActionService:
    return ChangesetActionService(repository, context.repositories.artifacts)


def review_feedback_action_service(
    repository: ChangesetRepository,
) -> ReviewFeedbackActionService:
    return ReviewFeedbackActionService(repository)


def review_feedback_fixup_inventory_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ReviewFeedbackFixupInventoryService:
    return ReviewFeedbackFixupInventoryService(
        repository, context.repositories.artifacts
    )


def manual_evidence_action_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ManualEvidenceActionService:
    return ManualEvidenceActionService(repository, context.repositories.artifacts)


def browser_evidence_action_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> BrowserEvidenceActionService:
    return BrowserEvidenceActionService(repository, context.repositories.artifacts)


def accessibility_evidence_action_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> AccessibilityEvidenceActionService:
    return AccessibilityEvidenceActionService(
        repository,
        context.repositories.artifacts,
    )


def changeset_verification_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetVerificationService:
    return ChangesetVerificationService(repository, context.repositories.artifacts)


def changeset_review_brief_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetReviewBriefService:
    return ChangesetReviewBriefService(repository, context.repositories.artifacts)


def commit_message_suggestion_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetCommitMessageSuggestionService:
    return ChangesetCommitMessageSuggestionService(
        repository,
        context.repositories.artifacts,
    )


def commit_readiness_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetCommitReadinessService:
    return ChangesetCommitReadinessService(repository, context.repositories.artifacts)


def handoff_readiness_service(
    context: RuntimeContext,
    repository: ChangesetRepository,
) -> ChangesetHandoffReadinessService:
    return ChangesetHandoffReadinessService(repository, context.repositories.artifacts)


def workspace_root_for_changeset(
    repository: ChangesetRepository,
    changeset_id: UUID,
) -> Path:
    changeset = repository.get_changeset(changeset_id)
    if changeset is None:
        raise ValueError(f"unknown changeset: {changeset_id}")
    return workspace_root_for_session(
        repository=repository,
        session_id=changeset.session_id,
    )


def workspace_root_for_session(
    *,
    repository: ChangesetRepository,
    session_id: UUID,
) -> Path:
    session = repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session: {session_id}")
    return session.cwd


__all__ = [
    "accessibility_evidence_action_service",
    "browser_evidence_action_service",
    "changeset_action_service",
    "changeset_derivation_service",
    "changeset_query_service",
    "changeset_repository",
    "changeset_review_brief_service",
    "changeset_verification_service",
    "commit_message_suggestion_service",
    "commit_readiness_service",
    "handoff_readiness_service",
    "manual_evidence_action_service",
    "review_feedback_action_service",
    "review_feedback_fixup_inventory_service",
    "workspace_root_for_changeset",
    "workspace_root_for_session",
]
