"""Changeset detail read-model assembly helpers."""

from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.changeset_command_evidence import (
    changeset_command_evidence_summary,
)
from glassbox.runtime.changeset_inventory_status import inventory_status
from glassbox.runtime.changeset_inventory_status import inventory_with_status_freshness
from glassbox.runtime.changeset_inventory_status import review_fixup_inventory_freshness
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.changeset_verification_plan_summary import (
    build_changeset_verification_plan_summary,
)
from glassbox.runtime.review_response_summary import changeset_review_response_summary
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus
from glassbox.runtime.review_responses import (
    review_feedback_response_status as _review_feedback_response_status,
)


def build_changeset_detail_view(
    repository: ChangesetRepository,
    changeset_id: ChangesetId,
    *,
    workspace_root: Path | None = None,
) -> ChangesetDetailView:
    """Assemble the transport-agnostic detail read model for one changeset."""

    changeset = repository.get_changeset(changeset_id)
    if changeset is None:
        raise ValueError(f"unknown changeset: {changeset_id}")
    sources = repository.list_changeset_sources(
        changeset.session_id,
        changeset.changeset_id,
    )
    inventory = repository.get_changeset_inventory(
        changeset.session_id,
        changeset.changeset_id,
    )
    verification_posture = repository.get_changeset_verification_posture(
        changeset.session_id,
        changeset.changeset_id,
    )
    review_briefs = repository.list_changeset_review_briefs(
        changeset.session_id,
        changeset.changeset_id,
    )
    review_feedback = repository.list_review_feedback(
        session_id=changeset.session_id,
        changeset_id=changeset.changeset_id,
        include_archived=True,
    )
    manual_evidence = repository.list_manual_evidence(
        session_id=changeset.session_id,
        changeset_id=changeset.changeset_id,
        include_archived=True,
        include_rejected=True,
        include_superseded=True,
    )
    response_summary = review_response_summary(
        repository,
        changeset,
        feedback=review_feedback,
        workspace_root=workspace_root,
    )
    readiness = repository.list_changeset_readiness(
        changeset.session_id,
        changeset.changeset_id,
    )
    status = inventory_status(
        changeset,
        inventory,
        workspace_root=workspace_root,
    )
    inventory_for_detail = inventory_with_status_freshness(inventory, status)
    command_evidence = changeset_command_evidence_summary(repository, changeset)
    task_ledger = (
        repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )
        if changeset.task_id is not None
        else []
    )
    return ChangesetDetailView(
        changeset=changeset,
        sources=sources,
        inventory=inventory_for_detail,
        verification_posture=verification_posture,
        inventory_status=status,
        review_briefs=review_briefs,
        review_feedback=review_feedback,
        manual_evidence=manual_evidence,
        review_response_summary=response_summary,
        readiness=readiness,
        command_evidence=command_evidence,
        verification_plan_summary=build_changeset_verification_plan_summary(
            task_ledger=task_ledger,
            safe_next_actions=detail_safe_next_actions(changeset, status),
        ),
        limitations=detail_limitations(
            changeset,
            sources,
            inventory_for_detail,
            status,
        ),
        safe_next_actions=detail_safe_next_actions(changeset, status),
    )


def review_feedback_response_status(
    repository: ChangesetRepository,
    feedback_id: ReviewFeedbackId,
    *,
    workspace_root: Path | None = None,
) -> ReviewFeedbackResponseStatus:
    """Build response status for one review-feedback item."""

    feedback = repository.get_review_feedback(feedback_id)
    if feedback is None:
        raise ValueError(f"unknown review feedback: {feedback_id}")
    inventories = repository.list_review_feedback_fixup_inventories(
        feedback.session_id,
        feedback.feedback_id,
    )
    paths = (
        repository.list_review_feedback_fixup_paths(
            feedback.session_id,
            feedback.feedback_id,
            inventories[0].artifact_id,
        )
        if inventories
        else []
    )
    freshness = (
        review_fixup_inventory_freshness(inventories[0], workspace_root)
        if workspace_root is not None and inventories
        else None
    )
    changeset = repository.get_changeset(feedback.changeset_id)
    task_ledger = (
        repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )
        if changeset is not None and changeset.task_id is not None
        else None
    )
    return _review_feedback_response_status(
        feedback=feedback,
        inventories=inventories,
        paths=paths,
        freshness_status=freshness,
        task_ledger=task_ledger,
    )


def review_response_summary(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
    *,
    feedback: list[ReviewFeedbackRecord] | None = None,
    workspace_root: Path | None = None,
) -> ChangesetReviewResponseSummary:
    feedback_items = (
        feedback
        if feedback is not None
        else repository.list_review_feedback(
            session_id=changeset.session_id,
            changeset_id=changeset.changeset_id,
            include_archived=True,
        )
    )
    statuses: list[ReviewFeedbackResponseStatus] = []
    task_ledger = (
        repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )
        if changeset.task_id is not None
        else None
    )
    for item in feedback_items:
        inventories = repository.list_review_feedback_fixup_inventories(
            item.session_id,
            item.feedback_id,
        )
        paths = (
            repository.list_review_feedback_fixup_paths(
                item.session_id,
                item.feedback_id,
                inventories[0].artifact_id,
            )
            if inventories
            else []
        )
        freshness = (
            review_fixup_inventory_freshness(inventories[0], workspace_root)
            if workspace_root is not None and inventories
            else None
        )
        statuses.append(
            _review_feedback_response_status(
                feedback=item,
                inventories=inventories,
                paths=paths,
                freshness_status=freshness,
                task_ledger=task_ledger,
            )
        )
    return changeset_review_response_summary(
        changeset_id=changeset.changeset_id,
        items=statuses,
    )


def review_response_summary_for_preview(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
    *,
    workspace_root: Path,
) -> ChangesetReviewResponseSummary:
    if not hasattr(repository, "list_review_feedback"):
        return changeset_review_response_summary(
            changeset_id=changeset.changeset_id,
            items=[],
        )
    return review_response_summary(
        repository,
        changeset,
        workspace_root=workspace_root,
    )


def review_feedback_for_preview(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
) -> list[ReviewFeedbackRecord]:
    if not hasattr(repository, "list_review_feedback"):
        return []
    return repository.list_review_feedback(
        session_id=changeset.session_id,
        changeset_id=changeset.changeset_id,
        include_archived=True,
    )


def manual_evidence_for_preview(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
) -> list[ManualEvidenceRecord]:
    if not hasattr(repository, "list_manual_evidence"):
        return []
    return repository.list_manual_evidence(
        session_id=changeset.session_id,
        changeset_id=changeset.changeset_id,
        include_archived=True,
        include_rejected=True,
        include_superseded=True,
    )


def detail_limitations(
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
    inventory: ChangesetInventoryRecord | None,
    status: ChangesetInventoryStatus,
) -> list[str]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    if inventory is None:
        limitations.append(
            "no structured change inventory is attached yet; inspect sources first"
        )
    if status.stale:
        limitations.append(
            status.reason
            or "structured change inventory is stale against the current workspace"
        )
    elif status.reason is not None and status.freshness == (
        ChangesetInventoryFreshness.UNKNOWN
    ):
        limitations.append(status.reason)
    if changeset.risk_level.value == "high":
        summary = changeset.risk_summary or "path classification marked high risk"
        limitations.append(f"high review risk: {summary}")
    return limitations


def detail_safe_next_actions(
    changeset: ChangesetRecord,
    status: ChangesetInventoryStatus,
) -> list[str]:
    actions = [show_changeset_command(changeset.changeset_id)]
    if changeset.status != "archived":
        actions.extend(status.safe_next_actions)
        actions.append(
            "glassbox eval recommend PATH --cwd .  # inspect verification options"
        )
    return list(dict.fromkeys(actions))


__all__ = [
    "build_changeset_detail_view",
    "changeset_command_evidence_summary",
    "detail_limitations",
    "detail_safe_next_actions",
    "manual_evidence_for_preview",
    "review_feedback_for_preview",
    "review_feedback_response_status",
    "review_response_summary",
    "review_response_summary_for_preview",
]
