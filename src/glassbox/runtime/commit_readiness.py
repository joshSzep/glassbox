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
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId
from glassbox.runtime.changesets import ChangesetInventoryStatus
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ChangesetVerificationService
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
    signals.extend(_recorded_commit_evidence_signals(readiness))
    signals.extend(_path_risk_signals(workspace_diff))
    signals.extend(_accepted_risk_signals(changeset, verification_plan))

    state = _aggregate_commit_state(signals)
    blockers = [signal.summary for signal in signals if signal.blocking]
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
        accepted_risk_count=changeset.accepted_risk_count
        + verification_plan.readiness.accepted_risk_count,
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
    review_decision = _latest_readiness(readiness, ChangesetReadinessKind.REVIEW)
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


def _recorded_commit_evidence_signals(
    readiness: Sequence[ChangesetReadinessRecord],
) -> list[CommitReadinessSignal]:
    commit_decision = _latest_readiness(readiness, ChangesetReadinessKind.COMMIT)
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
) -> list[CommitReadinessSignal]:
    accepted_count = (
        changeset.accepted_risk_count + verification_plan.readiness.accepted_risk_count
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
    blocking_states = [signal.state for signal in signals if signal.blocking]
    for state in (
        ChangesetReadinessState.BLOCKED,
        ChangesetReadinessState.STALE_INVENTORY,
        ChangesetReadinessState.DIRTY_UNTRACKED_RISK,
        ChangesetReadinessState.FAILED_CHECKS,
        ChangesetReadinessState.NEEDS_VERIFICATION,
        ChangesetReadinessState.MISSING_PROVENANCE,
        ChangesetReadinessState.NEEDS_REVIEW,
        ChangesetReadinessState.NOT_READY,
    ):
        if state in blocking_states:
            return state
    if any(
        signal.state == ChangesetReadinessState.ACCEPTED_WITH_RISK for signal in signals
    ):
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
    signal_ids = {signal.signal_id for signal in signals}
    if "inventory-missing" in signal_ids or "inventory-stale" in signal_ids:
        actions.append("glassbox changeset refresh CHANGESET --cwd .")
    if "verification-readiness" in signal_ids:
        actions.extend(verification_actions)
    if "review-brief-missing" in signal_ids or any(
        signal.signal_id.startswith("review-brief-stale") for signal in signals
    ):
        actions.append("glassbox changeset brief CHANGESET --cwd .")
    if "dirty-worktree" in signal_ids or "staged-empty" in signal_ids:
        actions.append("git status --short")
    if state in {
        ChangesetReadinessState.READY,
        ChangesetReadinessState.ACCEPTED_WITH_RISK,
    }:
        actions.append("git status --short")
    return list(dict.fromkeys(action for action in actions if action))[:20]


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


def _latest_readiness(
    readiness: Sequence[ChangesetReadinessRecord],
    kind: ChangesetReadinessKind,
) -> ChangesetReadinessRecord | None:
    for item in readiness:
        if item.readiness_kind == kind:
            return item
    return None


__all__ = [
    "ChangesetCommitReadinessService",
    "CommitReadinessAssessment",
    "CommitReadinessGitSummary",
    "CommitReadinessSignal",
    "derive_commit_readiness",
]
