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
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_queries import ChangesetQueryService
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_safe_commands import changeset_brief_command
from glassbox.runtime.changeset_safe_commands import changeset_evidence_list_command
from glassbox.runtime.changeset_safe_commands import changeset_feedback_status_command
from glassbox.runtime.changeset_safe_commands import changeset_refresh_command
from glassbox.runtime.changeset_verification import ChangesetVerificationService
from glassbox.runtime.review_readiness_signals import blocking_signal_summaries
from glassbox.runtime.review_readiness_signals import dedupe_actions
from glassbox.runtime.review_readiness_signals import first_blocking_state
from glassbox.runtime.review_readiness_signals import has_signal_prefix
from glassbox.runtime.review_readiness_signals import has_signal_state
from glassbox.runtime.review_readiness_signals import latest_readiness
from glassbox.runtime.review_readiness_signals import signal_ids
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.services import ArtifactRepository
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool
from glassbox.tools.workflow import GitStatusArgs
from glassbox.tools.workflow import GitStatusResult
from glassbox.tools.workflow import GitStatusTool


class CommitReadinessSignal(BaseModel):
    """One deterministic reason that contributes to commit readiness."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1, max_length=200)
    state: ChangesetReadinessState
    summary: str = Field(min_length=1, max_length=2000)
    blocking: bool = True
    paths: list[str] = Field(default_factory=list, max_length=100)


class CommitReadinessGitSummary(BaseModel):
    """Bounded git status and diff posture used by commit readiness."""

    model_config = ConfigDict(extra="forbid")

    branch: str | None = None
    ahead: int = 0
    behind: int = 0
    staged_paths: list[str] = Field(default_factory=list, max_length=200)
    unstaged_paths: list[str] = Field(default_factory=list, max_length=200)
    untracked_paths: list[str] = Field(default_factory=list, max_length=200)
    workspace_path_count: int = 0
    staged_path_count: int = 0
    policy_sensitive_paths: list[str] = Field(default_factory=list, max_length=100)
    generated_paths: list[str] = Field(default_factory=list, max_length=100)
    clean: bool = False
    error: str | None = None


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

    signals: list[CommitReadinessSignal] = []
    signals.extend(_tool_error_signals(git_status, workspace_diff, staged_diff))
    signals.extend(_inventory_signals(inventory, inventory_status))
    signals.extend(_git_workspace_signals(git_status, workspace_diff, staged_diff))
    signals.extend(_provenance_signals(changeset, inventory))
    signals.extend(_verification_signals(verification_plan))
    signals.extend(_review_signals(changeset, inventory, review_briefs, readiness))
    signals.extend(_review_loop_signals(review_response_summary))
    signals.extend(_manual_evidence_signals(manual_evidence))
    signals.extend(_recorded_commit_evidence_signals(readiness))
    signals.extend(_path_risk_signals(workspace_diff))
    signals.extend(
        _accepted_risk_signals(changeset, verification_plan, review_response_summary)
    )

    state = _aggregate_commit_state(signals)
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
    safe_next_actions = _safe_next_actions(
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
        git=_git_summary(git_status, workspace_diff, staged_diff),
        signals=signals,
        non_claims=[
            "commit readiness is advisory local posture, not permission to commit",
            "this model does not stage files or run git commit",
            "stale inventory or verification is not treated as fresh",
            "untracked and unstaged files can change what a commit actually contains",
        ],
    )


def _tool_error_signals(
    git_status: GitStatusResult,
    workspace_diff: DiffSummaryResult,
    staged_diff: DiffSummaryResult | None,
) -> list[CommitReadinessSignal]:
    signals: list[CommitReadinessSignal] = []
    if git_status.error is not None:
        signals.append(
            CommitReadinessSignal(
                signal_id="git-status-error",
                state=ChangesetReadinessState.BLOCKED,
                summary=f"git status could not be read: {git_status.error}",
            )
        )
    if workspace_diff.error is not None:
        signals.append(
            CommitReadinessSignal(
                signal_id="workspace-diff-error",
                state=ChangesetReadinessState.BLOCKED,
                summary=f"workspace diff could not be read: {workspace_diff.error}",
            )
        )
    if staged_diff is not None and staged_diff.error is not None:
        signals.append(
            CommitReadinessSignal(
                signal_id="staged-diff-error",
                state=ChangesetReadinessState.BLOCKED,
                summary=f"staged diff could not be read: {staged_diff.error}",
            )
        )
    return signals


def _inventory_signals(
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
) -> list[CommitReadinessSignal]:
    if inventory is None:
        return [
            CommitReadinessSignal(
                signal_id="inventory-missing",
                state=ChangesetReadinessState.STALE_INVENTORY,
                summary="commit readiness requires a current structured inventory",
            )
        ]
    if inventory_status.stale or inventory_status.reason is not None:
        return [
            CommitReadinessSignal(
                signal_id="inventory-stale",
                state=ChangesetReadinessState.STALE_INVENTORY,
                summary=(
                    inventory_status.reason
                    or "structured change inventory is stale against the workspace"
                ),
            )
        ]
    return []


def _git_workspace_signals(
    git_status: GitStatusResult,
    workspace_diff: DiffSummaryResult,
    staged_diff: DiffSummaryResult | None,
) -> list[CommitReadinessSignal]:
    signals: list[CommitReadinessSignal] = []
    if workspace_diff.clean:
        signals.append(
            CommitReadinessSignal(
                signal_id="workspace-clean",
                state=ChangesetReadinessState.NOT_READY,
                summary="workspace diff is clean; there is nothing local to commit",
            )
        )
    if staged_diff is None or staged_diff.clean:
        signals.append(
            CommitReadinessSignal(
                signal_id="staged-empty",
                state=ChangesetReadinessState.NOT_READY,
                summary="no staged changes are present for a commit",
            )
        )
    dirty_paths = list(dict.fromkeys(git_status.modified + git_status.untracked))
    if dirty_paths:
        signals.append(
            CommitReadinessSignal(
                signal_id="dirty-worktree",
                state=ChangesetReadinessState.DIRTY_UNTRACKED_RISK,
                summary=(
                    "unstaged or untracked files make the commit contents ambiguous"
                ),
                paths=dirty_paths,
            )
        )
    if git_status.behind:
        signals.append(
            CommitReadinessSignal(
                signal_id="branch-behind",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary=f"current branch is behind its upstream by {git_status.behind}",
            )
        )
    return signals


def _provenance_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
) -> list[CommitReadinessSignal]:
    if inventory is None:
        return []
    missing: list[str] = []
    if changeset.task_id is None and changeset.branch_candidate_id is None:
        missing.append("changeset is not linked to a task or branch candidate")
    if inventory.changed_path_count > 0 and inventory.source_digest is None:
        missing.append("inventory has no source digest")
    if not missing:
        return []
    return [
        CommitReadinessSignal(
            signal_id="provenance-missing",
            state=ChangesetReadinessState.MISSING_PROVENANCE,
            summary="; ".join(missing),
        )
    ]


def _verification_signals(
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[CommitReadinessSignal]:
    readiness = verification_plan.readiness
    if readiness.state in {
        ChangesetVerificationState.PASSED,
        ChangesetVerificationState.NOT_APPLICABLE,
    }:
        return []
    state = {
        ChangesetVerificationState.FAILED: ChangesetReadinessState.FAILED_CHECKS,
        ChangesetVerificationState.STALE: ChangesetReadinessState.STALE_INVENTORY,
        ChangesetVerificationState.ACCEPTED_WITH_RISK: (
            ChangesetReadinessState.ACCEPTED_WITH_RISK
        ),
    }.get(readiness.state, ChangesetReadinessState.NEEDS_VERIFICATION)
    return [
        CommitReadinessSignal(
            signal_id="verification-readiness",
            state=state,
            summary=readiness.summary,
            blocking=state != ChangesetReadinessState.ACCEPTED_WITH_RISK,
        )
    ]


def _review_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    review_briefs: Sequence[ChangesetReviewBriefRecord],
    readiness: Sequence[ChangesetReadinessRecord],
) -> list[CommitReadinessSignal]:
    latest_brief = review_briefs[0] if review_briefs else None
    if latest_brief is None:
        return [
            CommitReadinessSignal(
                signal_id="review-brief-missing",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary="no review brief has been generated for this changeset",
            )
        ]
    signals: list[CommitReadinessSignal] = []
    if (
        inventory is not None
        and latest_brief.inventory_artifact_id is not None
        and latest_brief.inventory_artifact_id != inventory.artifact_id
    ):
        signals.append(
            CommitReadinessSignal(
                signal_id="review-brief-stale-inventory",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary="latest review brief does not reference the current inventory",
            )
        )
    if (
        changeset.latest_verification_id is not None
        and latest_brief.verification_id is not None
        and latest_brief.verification_id != changeset.latest_verification_id
    ):
        signals.append(
            CommitReadinessSignal(
                signal_id="review-brief-stale-verification",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary=(
                    "latest review brief does not reference the current "
                    "verification posture"
                ),
            )
        )
    review_decision = latest_readiness(readiness, ChangesetReadinessKind.REVIEW)
    if review_decision is not None and review_decision.state not in {
        ChangesetReadinessState.READY,
        ChangesetReadinessState.ACCEPTED_WITH_RISK,
    }:
        signals.append(
            CommitReadinessSignal(
                signal_id="review-readiness-not-ready",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary=f"review readiness is {review_decision.state.value}",
            )
        )
    return signals


def _review_loop_signals(
    review_response_summary: ChangesetReviewResponseSummary | None,
) -> list[CommitReadinessSignal]:
    if review_response_summary is None:
        return []
    signals: list[CommitReadinessSignal] = []
    if review_response_summary.unresolved_count > 0:
        signals.append(
            CommitReadinessSignal(
                signal_id="review-feedback-unresolved",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary=(
                    f"{review_response_summary.unresolved_count} review feedback "
                    "item(s) still need local response before commit preparation"
                ),
            )
        )
    if review_response_summary.stale_response_count > 0:
        signals.append(
            CommitReadinessSignal(
                signal_id="review-response-stale",
                state=ChangesetReadinessState.NEEDS_VERIFICATION,
                summary=(
                    f"{review_response_summary.stale_response_count} review "
                    "response item(s) need refreshed response verification"
                ),
            )
        )
    failed_response_count = sum(
        1
        for item in review_response_summary.items
        if item.verification_state == ChangesetVerificationState.FAILED
    )
    missing_response_count = sum(
        1
        for item in review_response_summary.items
        if item.verification_state == ChangesetVerificationState.MISSING
    )
    if failed_response_count > 0:
        signals.append(
            CommitReadinessSignal(
                signal_id="review-response-verification-failed",
                state=ChangesetReadinessState.FAILED_CHECKS,
                summary=(
                    f"{failed_response_count} review response verification "
                    "item(s) failed"
                ),
            )
        )
    if missing_response_count > 0:
        signals.append(
            CommitReadinessSignal(
                signal_id="review-response-verification-missing",
                state=ChangesetReadinessState.NEEDS_VERIFICATION,
                summary=(
                    f"{missing_response_count} review response verification "
                    "item(s) are missing"
                ),
            )
        )
    return signals


def _manual_evidence_signals(
    manual_evidence: Sequence[ManualEvidenceRecord],
) -> list[CommitReadinessSignal]:
    attached = [
        item for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
    ]
    if not attached:
        return []
    signals: list[CommitReadinessSignal] = []
    stale_or_needs_inspection = [
        item
        for item in attached
        if item.freshness
        in {ManualEvidenceFreshness.STALE, ManualEvidenceFreshness.NEEDS_INSPECTION}
    ]
    if stale_or_needs_inspection:
        signals.append(
            CommitReadinessSignal(
                signal_id="manual-evidence-needs-inspection",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary=(
                    f"{len(stale_or_needs_inspection)} manual evidence item(s) "
                    "need inspection before commit preparation"
                ),
            )
        )
    local_only_count = sum(1 for item in attached if item.local_only)
    if local_only_count > 0:
        signals.append(
            CommitReadinessSignal(
                signal_id="manual-evidence-local-only",
                state=ChangesetReadinessState.ACCEPTED_WITH_RISK,
                summary=(
                    f"{local_only_count} local-only manual evidence item(s) "
                    "remain advisory context, not retained command proof"
                ),
                blocking=False,
            )
        )
    return signals


def _recorded_commit_evidence_signals(
    readiness: Sequence[ChangesetReadinessRecord],
) -> list[CommitReadinessSignal]:
    commit_decision = latest_readiness(readiness, ChangesetReadinessKind.COMMIT)
    if commit_decision is None:
        return []
    blocking = commit_decision.state not in {
        ChangesetReadinessState.READY,
        ChangesetReadinessState.ACCEPTED_WITH_RISK,
    }
    return [
        CommitReadinessSignal(
            signal_id="retained-precommit-evidence",
            state=commit_decision.state,
            summary=f"retained commit evidence: {commit_decision.reason}",
            blocking=blocking,
        )
    ]


def _path_risk_signals(
    workspace_diff: DiffSummaryResult,
) -> list[CommitReadinessSignal]:
    signals: list[CommitReadinessSignal] = []
    risk = workspace_diff.risk_summary
    if risk.policy_sensitive_paths:
        signals.append(
            CommitReadinessSignal(
                signal_id="policy-sensitive-paths",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary="policy-sensitive paths require explicit review before commit",
                paths=risk.policy_sensitive_paths,
            )
        )
    if risk.generated_files:
        signals.append(
            CommitReadinessSignal(
                signal_id="generated-paths",
                state=ChangesetReadinessState.NEEDS_REVIEW,
                summary="generated files are present and should be checked for churn",
                blocking=False,
                paths=risk.generated_files,
            )
        )
    return signals


def _accepted_risk_signals(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
    review_response_summary: ChangesetReviewResponseSummary | None,
) -> list[CommitReadinessSignal]:
    accepted_count = (
        changeset.accepted_risk_count
        + verification_plan.readiness.accepted_risk_count
        + (
            review_response_summary.accepted_risk_count
            if review_response_summary is not None
            else 0
        )
    )
    if accepted_count == 0:
        return []
    return [
        CommitReadinessSignal(
            signal_id="accepted-risk",
            state=ChangesetReadinessState.ACCEPTED_WITH_RISK,
            summary=f"{accepted_count} accepted risk item(s) remain attached",
            blocking=False,
        )
    ]


def _aggregate_commit_state(
    signals: Sequence[CommitReadinessSignal],
) -> ChangesetReadinessState:
    blocking_state = first_blocking_state(
        signals,
        (
            ChangesetReadinessState.BLOCKED,
            ChangesetReadinessState.STALE_INVENTORY,
            ChangesetReadinessState.DIRTY_UNTRACKED_RISK,
            ChangesetReadinessState.FAILED_CHECKS,
            ChangesetReadinessState.NEEDS_VERIFICATION,
            ChangesetReadinessState.MISSING_PROVENANCE,
            ChangesetReadinessState.NEEDS_REVIEW,
            ChangesetReadinessState.NOT_READY,
        ),
    )
    if blocking_state is not None:
        return blocking_state
    if has_signal_state(signals, ChangesetReadinessState.ACCEPTED_WITH_RISK):
        return ChangesetReadinessState.ACCEPTED_WITH_RISK
    return ChangesetReadinessState.READY


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


def _safe_next_actions(
    state: ChangesetReadinessState,
    signals: Sequence[CommitReadinessSignal],
    verification_actions: Sequence[str],
) -> list[str]:
    actions: list[str] = []
    ids = signal_ids(signals)
    if "inventory-missing" in ids or "inventory-stale" in ids:
        actions.append(changeset_refresh_command("CHANGESET"))
    if "verification-readiness" in ids:
        actions.extend(verification_actions)
    if has_signal_prefix(signals, "review-feedback"):
        actions.append(changeset_feedback_status_command("CHANGESET"))
    if has_signal_prefix(signals, "review-response"):
        actions.extend(verification_actions)
        actions.append(changeset_feedback_status_command("CHANGESET"))
    if "manual-evidence-needs-inspection" in ids:
        actions.append(changeset_evidence_list_command("CHANGESET"))
    if "review-brief-missing" in ids or has_signal_prefix(
        signals,
        "review-brief-stale",
    ):
        actions.append(changeset_brief_command("CHANGESET"))
    if "dirty-worktree" in ids or "staged-empty" in ids:
        actions.append("git status --short")
    if state in {
        ChangesetReadinessState.READY,
        ChangesetReadinessState.ACCEPTED_WITH_RISK,
    }:
        actions.append("git status --short")
    return dedupe_actions(actions)


def _git_summary(
    git_status: GitStatusResult,
    workspace_diff: DiffSummaryResult,
    staged_diff: DiffSummaryResult | None,
) -> CommitReadinessGitSummary:
    staged_paths = list(dict.fromkeys(git_status.staged))
    unstaged_paths = list(dict.fromkeys(git_status.modified))
    untracked_paths = list(dict.fromkeys(git_status.untracked))
    return CommitReadinessGitSummary(
        branch=git_status.branch,
        ahead=git_status.ahead,
        behind=git_status.behind,
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
        workspace_path_count=workspace_diff.risk_summary.touched_files,
        staged_path_count=(
            staged_diff.risk_summary.touched_files if staged_diff is not None else 0
        ),
        policy_sensitive_paths=workspace_diff.risk_summary.policy_sensitive_paths,
        generated_paths=workspace_diff.risk_summary.generated_files,
        clean=git_status.clean,
        error=git_status.error or workspace_diff.error,
    )


__all__ = [
    "ChangesetCommitReadinessService",
    "CommitReadinessAssessment",
    "CommitReadinessGitSummary",
    "CommitReadinessSignal",
    "derive_commit_readiness",
]
