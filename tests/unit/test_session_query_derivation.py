"""Unit coverage for v16 operator queue derivation contracts."""

from datetime import UTC
from datetime import datetime

import pytest

from glassbox.core import ClaimSupportState
from glassbox.core import NextAction
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import OperatorQueueDedupeKey
from glassbox.core import OperatorQueueDedupeScope
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueEvidenceSummary
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState


def test_operator_queue_item_contract_preserves_domain_specific_meaning() -> None:
    item = _queue_item(
        family=OperatorQueueFamily.REVIEW_BLOCKING,
        state=OperatorQueueState.BLOCKED,
        priority=NextActionPriority.BLOCKED,
        blocking=True,
        action_needed=True,
        dismissal_policy=OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED,
    )

    assert item.family == OperatorQueueFamily.REVIEW_BLOCKING
    assert item.safe_next_action.kind == NextActionKind.REVIEW
    assert item.evidence_summary.support_state == ClaimSupportState.MISSING
    assert item.dedupe_key.scope == OperatorQueueDedupeScope.FAMILY_TARGET
    assert item.owner_surface == NextActionSurface.DASHBOARD
    assert item.model_dump(mode="json")["dismissal_policy"] == (
        "canonical_decision_required"
    )


def test_operator_queue_item_rejects_target_mismatch() -> None:
    item = _queue_item()
    action = item.safe_next_action.model_copy(
        update={
            "target": NextActionTarget(
                kind=NextActionTargetKind.SESSION,
                target_id="session-1",
            )
        }
    )

    with pytest.raises(ValueError, match="target kind"):
        OperatorQueueItem.model_validate(
            {**item.model_dump(), "safe_next_action": action.model_dump()}
        )


def test_operator_queue_item_rejects_unmarked_blocking_family() -> None:
    with pytest.raises(ValueError, match="blocking queue families"):
        _queue_item(family=OperatorQueueFamily.WORK_BLOCKING, blocking=False)


def test_operator_queue_item_rejects_optional_action_needed_item() -> None:
    with pytest.raises(ValueError, match="must not be optional"):
        _queue_item(
            priority=NextActionPriority.OPTIONAL,
            action_needed=True,
        )


def test_operator_queue_item_rejects_stale_flag_without_stale_state() -> None:
    with pytest.raises(ValueError, match="stale queue items"):
        _queue_item(state=OperatorQueueState.READY, stale=True)


def _queue_item(
    *,
    family: OperatorQueueFamily = OperatorQueueFamily.ADVISORY,
    state: OperatorQueueState = OperatorQueueState.ACTION_NEEDED,
    priority: NextActionPriority = NextActionPriority.ACTION_NEEDED,
    blocking: bool = False,
    action_needed: bool = False,
    stale: bool = False,
    dismissal_policy: OperatorQueueDismissalPolicy = (
        OperatorQueueDismissalPolicy.DISMISSIBLE_UNTIL_CHANGED
    ),
) -> OperatorQueueItem:
    target = NextActionTarget(
        kind=NextActionTargetKind.CHANGESET,
        target_id="changeset-1",
        label="Changeset changeset-1",
    )
    action = NextAction(
        action_id="review:changeset-1",
        title="Review changeset evidence",
        summary="Inspect missing review evidence before handoff.",
        kind=NextActionKind.REVIEW,
        priority=priority,
        severity=NextActionSeverity.HIGH,
        target=target,
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )
    evidence = NextActionEvidenceRef(
        kind=NextActionEvidenceKind.REVIEW_FEEDBACK,
        ref_id="feedback-1",
        summary="Reviewer feedback remains open.",
    )
    return OperatorQueueItem(
        item_id="queue:review:changeset-1",
        family=family,
        state=state,
        priority=priority,
        severity=NextActionSeverity.HIGH,
        target=target,
        owner_surface=NextActionSurface.DASHBOARD,
        owner_label="Changeset review",
        safe_next_action=action,
        evidence_summary=OperatorQueueEvidenceSummary(
            summary="Missing reviewer response evidence.",
            support_state=ClaimSupportState.MISSING,
            evidence_graph_id="graph:changeset:changeset-1",
            claim_id="claim:changeset:changeset-1:review-posture",
            missing_evidence=[evidence],
            limitation_count=1,
        ),
        dedupe_key=OperatorQueueDedupeKey(
            scope=OperatorQueueDedupeScope.FAMILY_TARGET,
            key="review_blocking:changeset:changeset-1",
            target=target,
        ),
        dismissal_policy=dismissal_policy,
        action_needed=action_needed,
        blocking=blocking,
        stale=stale,
        updated_at=datetime(2026, 5, 11, tzinfo=UTC),
    )
