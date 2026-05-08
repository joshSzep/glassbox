"""Advisory commit-readiness model for reviewable changesets."""

import asyncio
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_queries import ChangesetQueryService
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_verification import ChangesetVerificationService
from glassbox.runtime.commit_readiness_git import CommitReadinessGitSummary
from glassbox.runtime.commit_readiness_git import derive_commit_git_summary
from glassbox.runtime.commit_readiness_signals import CommitReadinessSignal
from glassbox.runtime.commit_readiness_signals import aggregate_commit_state
from glassbox.runtime.commit_readiness_signals import build_commit_readiness_signals
from glassbox.runtime.commit_readiness_signals import commit_safe_next_actions
from glassbox.runtime.review_readiness_signals import blocking_signal_summaries
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.services import ArtifactRepository
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool
from glassbox.tools.workflow import GitStatusArgs
from glassbox.tools.workflow import GitStatusResult
from glassbox.tools.workflow import GitStatusTool


class CommitReadinessAssessment(BaseModel):
    """Read-only advisory answer for whether a changeset is commit-ready."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    readiness_kind: ChangesetReadinessKind = ChangesetReadinessKind.COMMIT
    state: ChangesetReadinessState
    reason: str = Field(min_length=1, max_length=4000)
    blockers: list[str] = Field(default_factory=list, max_length=20)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    inventory_artifact_id: ArtifactId | None = None
    review_brief_artifact_id: ArtifactId | None = None
    verification_id: TaskVerificationId | None = None
    review_feedback_count: int = Field(default=0, ge=0)
    unresolved_feedback_count: int = Field(default=0, ge=0)
    stale_response_count: int = Field(default=0, ge=0)
    manual_evidence_count: int = Field(default=0, ge=0)
    local_only_evidence_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    git: CommitReadinessGitSummary
    signals: list[CommitReadinessSignal] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class ChangesetCommitReadinessService:
    """Preview local commit readiness without staging or committing."""

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
    ) -> CommitReadinessAssessment:
        """Collect local evidence and derive an advisory commit-readiness view."""

        detail = ChangesetQueryService(self._repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset_id, workspace_root)
        git_status_tool = GitStatusTool(workspace_root)
        diff_summary_tool = DiffSummaryTool(workspace_root)
        git_status, workspace_diff, staged_diff = await asyncio.gather(
            git_status_tool.execute(GitStatusArgs()),
            diff_summary_tool.execute(
                DiffSummaryArgs(scope=DiffSummaryScope.WORKSPACE)
            ),
            diff_summary_tool.execute(DiffSummaryArgs(scope=DiffSummaryScope.STAGED)),
        )
        return derive_commit_readiness(
            changeset=detail.changeset,
            inventory=detail.inventory,
            inventory_status=detail.inventory_status,
            verification_plan=verification_plan,
            review_briefs=detail.review_briefs,
            review_response_summary=detail.review_response_summary,
            manual_evidence=detail.manual_evidence,
            readiness=detail.readiness,
            git_status=git_status,
            workspace_diff=workspace_diff,
            staged_diff=staged_diff,
        )


def derive_commit_readiness(
    *,
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    review_briefs: Sequence[ChangesetReviewBriefRecord] = (),
    review_response_summary: ChangesetReviewResponseSummary | None = None,
    manual_evidence: Sequence[ManualEvidenceRecord] = (),
    readiness: Sequence[ChangesetReadinessRecord] = (),
    git_status: GitStatusResult,
    workspace_diff: DiffSummaryResult,
    staged_diff: DiffSummaryResult | None = None,
) -> CommitReadinessAssessment:
    """Derive commit readiness from already-retained and local read-only evidence."""

    signals = build_commit_readiness_signals(
        changeset=changeset,
        inventory=inventory,
        inventory_status=inventory_status,
        verification_plan=verification_plan,
        review_briefs=review_briefs,
        review_response_summary=review_response_summary,
        manual_evidence=manual_evidence,
        readiness=readiness,
        git_status=git_status,
        workspace_diff=workspace_diff,
        staged_diff=staged_diff,
    )

    state = aggregate_commit_state(signals)
    blockers = blocking_signal_summaries(signals)
    latest_brief = review_briefs[0] if review_briefs else None
    verification_id = (
        verification_plan.readiness.requirements[0].verification_id
        if verification_plan.readiness.requirements
        and verification_plan.readiness.requirements[0].verification_id is not None
        else None
    )
    if verification_id is None and changeset.latest_verification_id is not None:
        verification_id = changeset.latest_verification_id
    safe_next_actions = commit_safe_next_actions(
        state,
        signals,
        verification_plan.safe_next_actions,
    )
    return CommitReadinessAssessment(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        state=state,
        reason=_commit_readiness_reason(state, blockers),
        blockers=blockers[:20],
        safe_next_actions=safe_next_actions,
        inventory_artifact_id=inventory.artifact_id if inventory is not None else None,
        review_brief_artifact_id=(
            latest_brief.artifact_id if latest_brief is not None else None
        ),
        verification_id=verification_id,
        review_feedback_count=(
            review_response_summary.total_feedback_count
            if review_response_summary is not None
            else 0
        ),
        unresolved_feedback_count=(
            review_response_summary.unresolved_count
            if review_response_summary is not None
            else 0
        ),
        stale_response_count=(
            review_response_summary.stale_response_count
            if review_response_summary is not None
            else 0
        ),
        manual_evidence_count=sum(
            1 for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
        ),
        local_only_evidence_count=sum(
            1
            for item in manual_evidence
            if item.state == ManualEvidenceState.ATTACHED and item.local_only
        ),
        accepted_risk_count=changeset.accepted_risk_count
        + verification_plan.readiness.accepted_risk_count
        + (
            review_response_summary.accepted_risk_count
            if review_response_summary is not None
            else 0
        ),
        git=derive_commit_git_summary(git_status, workspace_diff, staged_diff),
        signals=signals,
        non_claims=[
            "commit readiness is advisory local posture, not permission to commit",
            "this model does not stage files or run git commit",
            "stale inventory or verification is not treated as fresh",
            "untracked and unstaged files can change what a commit actually contains",
        ],
    )


def _commit_readiness_reason(
    state: ChangesetReadinessState,
    blockers: Sequence[str],
) -> str:
    if blockers:
        return "; ".join(blockers[:5])
    if state == ChangesetReadinessState.READY:
        return "changeset has staged changes, fresh evidence, review, and verification"
    if state == ChangesetReadinessState.ACCEPTED_WITH_RISK:
        return "changeset is locally commit-ready with accepted risk still visible"
    return f"commit readiness is {state.value}"


__all__ = [
    "ChangesetCommitReadinessService",
    "CommitReadinessAssessment",
    "CommitReadinessGitSummary",
    "CommitReadinessSignal",
    "derive_commit_readiness",
]
