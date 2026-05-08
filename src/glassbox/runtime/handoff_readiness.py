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
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
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
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.changeset_verification import ChangesetVerificationService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.commit_readiness import CommitReadinessGitSummary
from glassbox.runtime.review_readiness_signals import blocking_signal_summaries
from glassbox.runtime.review_readiness_signals import dedupe_actions
from glassbox.runtime.review_readiness_signals import first_blocking_state
from glassbox.runtime.review_readiness_signals import has_signal_state
from glassbox.runtime.review_readiness_signals import latest_readiness
from glassbox.runtime.review_readiness_signals import limitations_for_signal_ids
from glassbox.runtime.review_readiness_signals import signal_ids
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.skipped_evidence import skipped_live_evidence_counts
from glassbox.runtime.skipped_evidence import skipped_live_evidence_items
from glassbox.services import ArtifactRepository

HandoffReadinessState = Literal[
    "not_ready",
    "needs_review_response",
    "needs_verification",
    "stale_inventory",
    "unresolved_risk",
    "handoff_ready",
    "commit_prep_ready",
    "publication_blocked",
    "accepted_with_risk",
]


class HandoffReadinessSignal(BaseModel):
    """One evidence-backed reason contributing to handoff readiness."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1, max_length=200)
    state: HandoffReadinessState
    summary: str = Field(min_length=1, max_length=2000)
    blocking: bool = True
    paths: list[str] = Field(default_factory=list, max_length=100)


class HandoffReadinessEvidenceSummary(BaseModel):
    """Small count summary for the evidence used in handoff readiness."""

    model_config = ConfigDict(extra="forbid")

    feedback_count: int = Field(ge=0)
    unresolved_feedback_count: int = Field(ge=0)
    stale_response_count: int = Field(ge=0)
    manual_evidence_count: int = Field(ge=0)
    local_only_evidence_count: int = Field(ge=0)
    stale_manual_evidence_count: int = Field(ge=0)
    needs_inspection_evidence_count: int = Field(ge=0)
    browser_evidence_count: int = Field(ge=0)
    accessibility_evidence_count: int = Field(ge=0)
    skipped_live_evidence_count: int = Field(ge=0)
    skipped_browser_evidence_count: int = Field(ge=0)
    skipped_accessibility_evidence_count: int = Field(ge=0)
    review_brief_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)


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

    signals: list[HandoffReadinessSignal] = []
    signals.extend(_publication_boundary_signals(changeset, commit_readiness))
    signals.extend(_provenance_signals(changeset, inventory))
    signals.extend(_inventory_signals(inventory, inventory_status))
    signals.extend(_review_response_signals(changeset, review_response_summary))
    signals.extend(_verification_signals(changeset, verification_plan))
    signals.extend(
        _brief_signals(changeset, inventory, verification_plan, review_briefs)
    )
    signals.extend(_risk_signals(changeset, verification_plan, review_response_summary))
    signals.extend(_manual_evidence_signals(changeset, manual_evidence))
    signals.extend(_prior_readiness_signals(readiness))

    blockers = blocking_signal_summaries(signals)
    latest_brief = review_briefs[0] if review_briefs else None
    state = _aggregate_handoff_state(signals, commit_readiness)
    safe_next_actions = _safe_next_actions(
        changeset.changeset_id,
        state,
        signals,
        verification_plan.safe_next_actions,
        review_response_summary.safe_next_actions,
    )
    limitations = _limitations(signals)
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
        commit_readiness_state=commit_readiness.state,
        evidence=_evidence_summary(
            review_response_summary,
            manual_evidence,
            review_briefs,
            changeset,
            verification_plan,
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


def _publication_boundary_signals(
    changeset: ChangesetRecord,
    commit_readiness: CommitReadinessAssessment,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if changeset.status != "active":
        signals.append(
            HandoffReadinessSignal(
                signal_id="changeset-not-active",
                state="publication_blocked",
                summary=(
                    f"changeset status is {changeset.status}; inspect archived or "
                    "replacement evidence before handoff"
                ),
            )
        )
    if commit_readiness.git.error is not None:
        signals.append(
            HandoffReadinessSignal(
                signal_id="git-inspection-error",
                state="publication_blocked",
                summary=(
                    f"git status could not be inspected: {commit_readiness.git.error}"
                ),
            )
        )
    dirty_paths = [
        path
        for path in dict.fromkeys(commit_readiness.git.untracked_paths)
        if not path.startswith(".glassbox/")
    ]
    if dirty_paths:
        signals.append(
            HandoffReadinessSignal(
                signal_id="dirty-workspace-ambiguity",
                state="not_ready",
                summary=(
                    "workspace has untracked paths; inspect before "
                    "treating handoff evidence as current"
                ),
                paths=dirty_paths[:100],
            )
        )
    return signals


def _provenance_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
) -> list[HandoffReadinessSignal]:
    if inventory is None and changeset.latest_inventory_artifact_id is None:
        return [
            HandoffReadinessSignal(
                signal_id="inventory-missing",
                state="stale_inventory",
                summary="handoff requires a structured changeset inventory",
            )
        ]
    return []


def _inventory_signals(
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
) -> list[HandoffReadinessSignal]:
    if inventory is None:
        return [
            HandoffReadinessSignal(
                signal_id="inventory-missing",
                state="stale_inventory",
                summary="structured changeset inventory is missing",
            )
        ]
    if (
        inventory_status.stale
        or inventory_status.freshness != ChangesetInventoryFreshness.FRESH
    ):
        return [
            HandoffReadinessSignal(
                signal_id="inventory-stale",
                state="stale_inventory",
                summary=(
                    inventory_status.reason
                    or "structured changeset inventory is stale or unknown"
                ),
            )
        ]
    return []


def _review_response_signals(
    changeset: ChangesetRecord,
    summary: ChangesetReviewResponseSummary,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if summary.unresolved_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="unresolved-review-feedback",
                state="needs_review_response",
                summary=(
                    f"{summary.unresolved_count} review feedback item"
                    f"{'' if summary.unresolved_count == 1 else 's'} still "
                    "need response"
                ),
            )
        )
    if summary.stale_response_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="stale-review-response",
                state="needs_review_response",
                summary=(
                    f"{summary.stale_response_count} review response"
                    f"{'' if summary.stale_response_count == 1 else 's'} "
                    "need inspection"
                ),
            )
        )
    for blocker in summary.blockers[:5]:
        signals.append(
            HandoffReadinessSignal(
                signal_id="review-response-blocker",
                state="needs_review_response",
                summary=blocker,
            )
        )
    if not signals and summary.total_feedback_count == 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="no-review-feedback",
                state="handoff_ready",
                summary=(
                    f"no local review feedback is attached to changeset "
                    f"{changeset.changeset_id}; handoff summary must not claim review"
                ),
                blocking=False,
            )
        )
    return signals


def _verification_signals(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[HandoffReadinessSignal]:
    readiness = verification_plan.readiness
    if readiness.state == ChangesetVerificationState.PASSED:
        return []
    return [
        HandoffReadinessSignal(
            signal_id="verification-not-passed",
            state="needs_verification",
            summary=(
                f"verification readiness is {readiness.state.value}: "
                f"{readiness.summary}"
            ),
            paths=verification_plan.changed_paths[:100],
        )
    ]


def _brief_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    review_briefs: Sequence[ChangesetReviewBriefRecord],
) -> list[HandoffReadinessSignal]:
    if not review_briefs:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-missing",
                state="not_ready",
                summary="handoff needs a current lifecycle review brief",
            )
        ]
    latest = review_briefs[0]
    if inventory is not None and latest.inventory_artifact_id != inventory.artifact_id:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-stale-inventory",
                state="not_ready",
                summary="latest lifecycle review brief does not cite current inventory",
            )
        ]
    verification_id = _verification_id(changeset, verification_plan)
    if verification_id is not None and latest.verification_id != verification_id:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-stale-verification",
                state="not_ready",
                summary=(
                    "latest lifecycle review brief does not cite current verification"
                ),
            )
        ]
    return []


def _risk_signals(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
    review_response_summary: ChangesetReviewResponseSummary,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if changeset.unresolved_risk_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="unresolved-risk",
                state="unresolved_risk",
                summary=(
                    f"{changeset.unresolved_risk_count} unresolved changeset risk"
                    f"{'' if changeset.unresolved_risk_count == 1 else 's'} remain"
                ),
            )
        )
    accepted_count = (
        changeset.accepted_risk_count
        + verification_plan.readiness.accepted_risk_count
        + review_response_summary.accepted_risk_count
    )
    if accepted_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="accepted-risk",
                state="accepted_with_risk",
                summary=(
                    f"{accepted_count} accepted risk"
                    f"{'' if accepted_count == 1 else 's'} must be visible in handoff"
                ),
                blocking=False,
            )
        )
    return signals


def _manual_evidence_signals(
    changeset: ChangesetRecord,
    manual_evidence: Sequence[ManualEvidenceRecord],
) -> list[HandoffReadinessSignal]:
    attached = [
        item for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
    ]
    signals: list[HandoffReadinessSignal] = []
    stale = [
        item for item in attached if item.freshness == ManualEvidenceFreshness.STALE
    ]
    needs_inspection = [
        item
        for item in attached
        if item.freshness == ManualEvidenceFreshness.NEEDS_INSPECTION
    ]
    if stale:
        signals.append(
            HandoffReadinessSignal(
                signal_id="stale-manual-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(stale)} manual evidence item"
                    f"{'' if len(stale) == 1 else 's'} are stale"
                ),
                blocking=False,
            )
        )
    if needs_inspection:
        signals.append(
            HandoffReadinessSignal(
                signal_id="manual-evidence-needs-inspection",
                state="handoff_ready",
                summary=(
                    f"{len(needs_inspection)} manual evidence item"
                    f"{'' if len(needs_inspection) == 1 else 's'} need inspection"
                ),
                blocking=False,
            )
        )
    local_only = [item for item in attached if item.local_only]
    skipped_live = skipped_live_evidence_items(attached)
    if local_only:
        signals.append(
            HandoffReadinessSignal(
                signal_id="local-only-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(local_only)} local-only evidence item"
                    f"{'' if len(local_only) == 1 else 's'} must remain labeled"
                ),
                blocking=False,
            )
        )
    if skipped_live:
        signals.append(
            HandoffReadinessSignal(
                signal_id="skipped-live-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(skipped_live)} skipped live evidence item"
                    f"{'' if len(skipped_live) == 1 else 's'} remain visible "
                    "as limitations, not passes"
                ),
                blocking=False,
            )
        )
    if not attached:
        signals.append(
            HandoffReadinessSignal(
                signal_id="no-manual-evidence",
                state="handoff_ready",
                summary=(
                    f"changeset {changeset.changeset_id} has no manual evidence; "
                    "do not imply external checks or reviewer observations"
                ),
                blocking=False,
            )
        )
    return signals


def _prior_readiness_signals(
    readiness: Sequence[ChangesetReadinessRecord],
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    review = latest_readiness(readiness, ChangesetReadinessKind.REVIEW)
    if review is not None and review.state != ChangesetReadinessState.READY:
        signals.append(
            HandoffReadinessSignal(
                signal_id="review-readiness-not-ready",
                state="not_ready",
                summary=(
                    f"latest review readiness is {review.state.value}: {review.reason}"
                ),
            )
        )
    return signals


def _aggregate_handoff_state(
    signals: Sequence[HandoffReadinessSignal],
    commit_readiness: CommitReadinessAssessment,
) -> HandoffReadinessState:
    blocking_state = first_blocking_state(
        signals,
        (
            "publication_blocked",
            "stale_inventory",
            "needs_review_response",
            "needs_verification",
            "not_ready",
            "unresolved_risk",
        ),
    )
    if blocking_state is not None:
        return blocking_state
    if has_signal_state(signals, "accepted_with_risk"):
        return "accepted_with_risk"
    if commit_readiness.state == ChangesetReadinessState.READY:
        return "commit_prep_ready"
    return "handoff_ready"


def _safe_next_actions(
    changeset_id: ChangesetId,
    state: HandoffReadinessState,
    signals: Sequence[HandoffReadinessSignal],
    verification_actions: Sequence[str],
    response_actions: Sequence[str],
) -> list[str]:
    actions = [
        show_changeset_command(changeset_id),
    ]
    ids = signal_ids(signals)
    if state == "stale_inventory" or "dirty-workspace-ambiguity" in ids:
        actions.append("git status --short")
        actions.append(changeset_refresh_command(changeset_id))
    if state == "needs_review_response":
        actions.append(changeset_feedback_status_command(changeset_id))
        actions.extend(response_actions)
    if state == "needs_verification":
        actions.append(changeset_verification_plan_command(changeset_id))
        actions.extend(verification_actions)
    if "lifecycle-brief-missing" in ids or state == "not_ready":
        actions.append(changeset_brief_command(changeset_id))
    if state in {"handoff_ready", "commit_prep_ready", "accepted_with_risk"}:
        actions.append(f"glassbox changeset handoff-readiness {changeset_id} --cwd .")
        actions.append(f"glassbox changeset commit-prep {changeset_id} --cwd .")
    if "local-only-evidence" in ids:
        actions.append(changeset_evidence_list_command(changeset_id))
    if "skipped-live-evidence" in ids:
        actions.append(changeset_evidence_list_command(changeset_id))
    return dedupe_actions(actions)


def _limitations(signals: Sequence[HandoffReadinessSignal]) -> list[str]:
    return limitations_for_signal_ids(
        signals,
        {
            "local-only-evidence": (
                "local-only evidence can support local handoff context but must be "
                "reviewed before export or publication"
            ),
            "stale-manual-evidence": (
                "stale manual evidence is advisory context and should be inspected "
                "before it is reused outside the local handoff"
            ),
            "manual-evidence-needs-inspection": (
                "manual evidence marked needs-inspection is advisory context, not "
                "fresh deterministic verification"
            ),
            "no-review-feedback": (
                "no retained review feedback exists; handoff must not claim "
                "reviewer input"
            ),
            "no-manual-evidence": (
                "no retained manual evidence exists; external checks or "
                "observations are not claimed"
            ),
            "skipped-live-evidence": (
                "skipped browser, dashboard, or accessibility evidence remains "
                "advisory context and is not a pass"
            ),
        }.items(),
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


def _evidence_summary(
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord],
    review_briefs: Sequence[ChangesetReviewBriefRecord],
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> HandoffReadinessEvidenceSummary:
    attached = [
        item for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
    ]
    (
        skipped_live_evidence_count,
        skipped_browser_evidence_count,
        skipped_accessibility_evidence_count,
    ) = skipped_live_evidence_counts(attached)
    return HandoffReadinessEvidenceSummary(
        feedback_count=review_response_summary.total_feedback_count,
        unresolved_feedback_count=review_response_summary.unresolved_count,
        stale_response_count=review_response_summary.stale_response_count,
        manual_evidence_count=len(attached),
        local_only_evidence_count=sum(1 for item in attached if item.local_only),
        stale_manual_evidence_count=sum(
            1 for item in attached if item.freshness == ManualEvidenceFreshness.STALE
        ),
        needs_inspection_evidence_count=sum(
            1
            for item in attached
            if item.freshness == ManualEvidenceFreshness.NEEDS_INSPECTION
        ),
        browser_evidence_count=sum(
            1
            for item in attached
            if item.evidence_kind
            in {ManualEvidenceKind.BROWSER_OBSERVATION, ManualEvidenceKind.SCREENSHOT}
        ),
        accessibility_evidence_count=sum(
            1
            for item in attached
            if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
        ),
        skipped_live_evidence_count=skipped_live_evidence_count,
        skipped_browser_evidence_count=skipped_browser_evidence_count,
        skipped_accessibility_evidence_count=skipped_accessibility_evidence_count,
        review_brief_count=len(review_briefs),
        accepted_risk_count=(
            changeset.accepted_risk_count
            + verification_plan.readiness.accepted_risk_count
            + review_response_summary.accepted_risk_count
        ),
    )
