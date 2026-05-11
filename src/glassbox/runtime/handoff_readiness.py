"""Advisory handoff-readiness model for review-loop changesets."""

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ManualEvidenceRecord
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanLifecycleSummary
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_queries import ChangesetQueryService
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_verification import ChangesetVerificationService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.commit_readiness import CommitReadinessGitSummary
from glassbox.runtime.handoff_readiness_evidence import HandoffReadinessEvidenceSummary
from glassbox.runtime.handoff_readiness_evidence import build_handoff_evidence_summary
from glassbox.runtime.handoff_readiness_signals import HandoffReadinessSignal
from glassbox.runtime.handoff_readiness_signals import HandoffReadinessState
from glassbox.runtime.handoff_readiness_signals import aggregate_handoff_state
from glassbox.runtime.handoff_readiness_signals import build_handoff_readiness_signals
from glassbox.runtime.handoff_readiness_signals import handoff_limitations
from glassbox.runtime.handoff_readiness_signals import handoff_safe_next_actions
from glassbox.runtime.review_readiness_signals import blocking_signal_summaries
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.services import ArtifactRepository


class HandoffReadinessAssessment(BaseModel):
    """Read-only advisory answer for final local handoff posture."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    readiness_kind: Literal["handoff"] = "handoff"
    state: HandoffReadinessState
    reason: str = Field(min_length=1, max_length=4000)
    blockers: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    inventory_artifact_id: ArtifactId | None = None
    review_brief_artifact_id: ArtifactId | None = None
    verification_id: TaskVerificationId | None = None
    verification_plan_summary: ChangesetVerificationPlanLifecycleSummary = Field(
        default_factory=lambda: ChangesetVerificationPlanLifecycleSummary()
    )
    commit_readiness_state: ChangesetReadinessState
    evidence: HandoffReadinessEvidenceSummary
    git: CommitReadinessGitSummary
    signals: list[HandoffReadinessSignal] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class ChangesetHandoffReadinessService:
    """Preview final handoff posture without any publication mutation."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def preview(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
    ) -> HandoffReadinessAssessment:
        """Collect retained review-loop evidence and derive handoff readiness."""

        query_service = ChangesetQueryService(self._repository)
        detail = query_service.get_detail(changeset_id, workspace_root=workspace_root)
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset_id, workspace_root)
        commit_readiness = await ChangesetCommitReadinessService(
            self._repository,
            self._artifact_repository,
        ).preview(changeset_id, workspace_root)
        return derive_handoff_readiness(
            changeset=detail.changeset,
            inventory=detail.inventory,
            inventory_status=detail.inventory_status,
            verification_plan=verification_plan,
            review_briefs=detail.review_briefs,
            review_response_summary=detail.review_response_summary,
            manual_evidence=detail.manual_evidence,
            readiness=detail.readiness,
            commit_readiness=commit_readiness,
        )


def preview_handoff_readiness(
    service: ChangesetHandoffReadinessService,
    changeset_id: ChangesetId,
    workspace_root: Path,
) -> HandoffReadinessAssessment:
    """Synchronous helper for CLI call sites."""

    return asyncio.run(service.preview(changeset_id, workspace_root))


def derive_handoff_readiness(
    *,
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    review_briefs: Sequence[ChangesetReviewBriefRecord] = (),
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord] = (),
    readiness: Sequence[ChangesetReadinessRecord] = (),
    commit_readiness: CommitReadinessAssessment,
) -> HandoffReadinessAssessment:
    """Derive final local handoff posture from retained evidence."""

    signals = build_handoff_readiness_signals(
        changeset=changeset,
        inventory=inventory,
        inventory_status=inventory_status,
        verification_plan=verification_plan,
        review_briefs=review_briefs,
        review_response_summary=review_response_summary,
        manual_evidence=manual_evidence,
        readiness=readiness,
        commit_readiness=commit_readiness,
    )

    blockers = blocking_signal_summaries(signals)
    latest_brief = review_briefs[0] if review_briefs else None
    state = aggregate_handoff_state(signals, commit_readiness)
    safe_next_actions = handoff_safe_next_actions(
        changeset_id=changeset.changeset_id,
        state=state,
        signals=signals,
        verification_actions=verification_plan.safe_next_actions,
        response_actions=review_response_summary.safe_next_actions,
    )
    limitations = handoff_limitations(signals)
    return HandoffReadinessAssessment(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        state=state,
        reason=_handoff_reason(state, blockers, limitations),
        blockers=blockers[:20],
        limitations=limitations,
        safe_next_actions=safe_next_actions,
        inventory_artifact_id=inventory.artifact_id if inventory is not None else None,
        review_brief_artifact_id=(
            latest_brief.artifact_id if latest_brief is not None else None
        ),
        verification_id=_verification_id(changeset, verification_plan),
        verification_plan_summary=verification_plan.plan_summary,
        commit_readiness_state=commit_readiness.state,
        evidence=build_handoff_evidence_summary(
            review_response_summary=review_response_summary,
            manual_evidence=manual_evidence,
            review_briefs=review_briefs,
            changeset=changeset,
            verification_plan=verification_plan,
        ),
        git=commit_readiness.git,
        signals=signals,
        non_claims=[
            "handoff readiness is advisory local posture, not publication",
            (
                "handoff-ready does not mean reviewed, approved, committed, "
                "pushed, or merged"
            ),
            (
                "manual, browser, dashboard, and accessibility evidence remains "
                "bounded by its retained summary"
            ),
            "skipped live evidence is retained as a limitation, not a pass",
            (
                "Glassbox did not stage, commit, push, open a pull request, "
                "merge, deploy, or publish"
            ),
        ],
    )


def _handoff_reason(
    state: HandoffReadinessState,
    blockers: Sequence[str],
    limitations: Sequence[str],
) -> str:
    if blockers:
        return f"{state.replace('_', ' ')}: {blockers[0]}"
    if state == "commit_prep_ready":
        return (
            "handoff evidence is coherent and commit preparation has no "
            "blocking signals"
        )
    if state == "accepted_with_risk":
        return (
            "handoff evidence is coherent with accepted risks that must remain visible"
        )
    if state == "handoff_ready":
        if limitations:
            return f"handoff evidence is coherent with limitations: {limitations[0]}"
        return "handoff evidence is coherent for final operator inspection"
    return state.replace("_", " ")


def _verification_id(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> TaskVerificationId | None:
    for requirement in verification_plan.readiness.requirements:
        if requirement.verification_id is not None:
            return requirement.verification_id
    return changeset.latest_verification_id
