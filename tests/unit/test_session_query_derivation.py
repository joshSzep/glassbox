"""Unit coverage for v16 operator queue derivation contracts."""

from datetime import UTC
from datetime import datetime
from typing import Literal

import pytest

from glassbox.core import ClaimSupportState
from glassbox.core import LongRunStatusRecord
from glassbox.core import MaintenanceCue
from glassbox.core import MaintenanceCueKind
from glassbox.core import NextAction
from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSafetyClass
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
from glassbox.core import ProjectionHealth
from glassbox.core import new_session_id
from glassbox.runtime.operator_queue import build_operator_queue
from glassbox.runtime.operator_queue import dedupe_operator_queue_items
from glassbox.runtime.operator_queue import operator_queue_counts
from glassbox.runtime.operator_queue import sort_operator_queue_items
from glassbox.runtime.operator_queue_changeset_items import build_changeset_queue_items
from glassbox.runtime.operator_session_queries import build_operator_session_summary
from glassbox.runtime.session_query_models import SessionSummaryView
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView


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


def test_runtime_operator_queue_prioritizes_and_counts_session_attention() -> None:
    approval = build_operator_session_summary(
        _session_summary(pending_approval_id="approval-1")
    )
    failed = build_operator_session_summary(
        _session_summary(status="failed", failure="provider failed")
    )
    active = build_operator_session_summary(_session_summary(active=True))
    runtime = WorkspaceRuntimeSummaryView(
        workspace_root="/tmp/glassbox",
        state="running",
        background_job_failed_count=1,
    )

    queue = build_operator_queue([active, failed, approval], runtime=runtime)
    counts = operator_queue_counts(queue)

    assert [item.owner_label for item in queue[:3]] == [
        "Pending approval",
        "Failed session",
        "Background jobs",
    ]
    assert counts.work_blocking == 2
    assert counts.maintenance == 1
    assert counts.informational == 1
    assert queue[0].dismissal_policy == (
        OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED
    )


def test_runtime_operator_queue_projects_maintenance_cues_after_active_work() -> None:
    approval = build_operator_session_summary(
        _session_summary(pending_approval_id="approval-1")
    )
    target = NextActionTarget(
        kind=NextActionTargetKind.WORKSPACE,
        target_id="/tmp/glassbox",
        label="Workspace",
    )
    runtime = WorkspaceRuntimeSummaryView(
        workspace_root="/tmp/glassbox",
        state="running",
        maintenance_cues=[
            MaintenanceCue(
                cue_id="maintenance:/tmp/glassbox:backup_posture",
                kind=MaintenanceCueKind.BACKUP_POSTURE,
                title="Backup posture",
                summary="No retained workspace backup archive was found.",
                priority=NextActionPriority.RECOMMENDED,
                severity=NextActionSeverity.INFO,
                target=target,
                safe_next_actions=[
                    NextAction(
                        action_id="backup:create",
                        title="Create a workspace backup",
                        summary="Capture state before maintenance.",
                        kind=NextActionKind.MAINTAIN,
                        priority=NextActionPriority.RECOMMENDED,
                        severity=NextActionSeverity.INFO,
                        safety_class=NextActionSafetyClass.COMMAND_RECIPE,
                        target=target,
                        command=NextActionCommandRecipe(
                            command=["glassbox", "backup", "create", "--cwd", "."],
                            display="glassbox backup create --cwd .",
                            purpose="Capture state before maintenance.",
                        ),
                    )
                ],
                missing_evidence=[
                    NextActionEvidenceRef(
                        kind=NextActionEvidenceKind.ARTIFACT,
                        ref_id="/tmp/glassbox/.glassbox/backups",
                        summary="No local backup archive was found.",
                        freshness="missing",
                    )
                ],
            )
        ],
    )

    queue = build_operator_queue([approval], runtime=runtime)
    counts = operator_queue_counts(queue)
    maintenance = next(
        item for item in queue if item.family == OperatorQueueFamily.MAINTENANCE
    )

    assert [item.family for item in queue] == [
        OperatorQueueFamily.WORK_BLOCKING,
        OperatorQueueFamily.MAINTENANCE,
    ]
    assert counts.work_blocking == 1
    assert counts.maintenance == 1
    assert maintenance.state == OperatorQueueState.WATCHING
    assert maintenance.action_needed is False
    assert maintenance.safe_next_action.command is not None
    assert maintenance.safe_next_action.command.display == (
        "glassbox backup create --cwd ."
    )


def test_runtime_operator_queue_characterizes_question_long_run_and_active_rows() -> (
    None
):
    question = build_operator_session_summary(
        _session_summary(pending_question_id="question-1")
    )
    stale_long_run = build_operator_session_summary(
        _session_summary(
            active=True,
            long_run_state="stale",
            long_run_summary="Tool output has not advanced recently.",
        )
    )
    active = build_operator_session_summary(_session_summary(active=True))
    runtime = WorkspaceRuntimeSummaryView(
        workspace_root="/tmp/glassbox",
        state="running",
    )

    queue = build_operator_queue([active, stale_long_run, question], runtime=runtime)

    assert [(item.owner_label, item.family, item.state) for item in queue] == [
        (
            "Pending question",
            OperatorQueueFamily.WORK_BLOCKING,
            OperatorQueueState.ACTION_NEEDED,
        ),
        (
            "Long-running session",
            OperatorQueueFamily.WORK_BLOCKING,
            OperatorQueueState.STALE,
        ),
        (
            "Active turn",
            OperatorQueueFamily.INFORMATIONAL,
            OperatorQueueState.ACTIVE,
        ),
        (
            "Active turn",
            OperatorQueueFamily.INFORMATIONAL,
            OperatorQueueState.ACTIVE,
        ),
    ]
    assert queue[0].safe_next_action.kind == NextActionKind.ANSWER
    assert queue[0].dismissal_policy == (
        OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED
    )
    assert queue[1].stale is True
    assert queue[1].blocking is True
    assert queue[1].evidence_summary.stale_evidence[0].freshness == "stale"
    assert all(item.action_needed is False for item in queue[2:])


def test_runtime_operator_queue_dedupes_by_key_and_keeps_stronger_item() -> None:
    weak = _queue_item(
        priority=NextActionPriority.RECOMMENDED,
        action_needed=False,
    )
    strong = _queue_item(
        priority=NextActionPriority.BLOCKED,
        blocking=True,
        action_needed=True,
        family=OperatorQueueFamily.WORK_BLOCKING,
    )

    deduped = dedupe_operator_queue_items([weak, strong])

    assert deduped == [strong]
    assert sort_operator_queue_items([weak, strong])[0] == strong


def test_operator_queue_keeps_changeset_source_gap_explicit() -> None:
    runtime = WorkspaceRuntimeSummaryView(
        workspace_root="/tmp/glassbox",
        state="running",
    )

    queue = build_operator_queue([], runtime=runtime)

    assert build_changeset_queue_items() == []
    assert all(item.target.kind != NextActionTargetKind.CHANGESET for item in queue)


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


def _session_summary(
    *,
    status: str = "running",
    pending_approval_id: str | None = None,
    pending_question_id: str | None = None,
    failure: str | None = None,
    active: bool = False,
    long_run_state: Literal[
        "healthy",
        "idle",
        "paused",
        "stale",
        "stuck",
        "completed",
    ] = "healthy",
    long_run_summary: str = "healthy",
) -> SessionSummaryView:
    session_id = new_session_id()
    now = datetime(2026, 5, 11, tzinfo=UTC)
    return SessionSummaryView(
        session_id=session_id,
        status=(
            "awaiting_approval"
            if pending_approval_id is not None
            else "awaiting_user_input"
            if pending_question_id is not None
            else status
        ),
        model_name="openai:gpt-5.4",
        cwd="/tmp/glassbox",
        approval_mode="confirm",
        can_fork=False,
        created_at=now,
        updated_at=now,
        last_sequence=3,
        pending_approval_id=pending_approval_id,
        pending_question_id=pending_question_id,
        session_failure_message=failure,
        session_failure_retryable=None if failure is None else False,
        long_run_status=LongRunStatusRecord(
            state=long_run_state,
            elapsed_seconds=5,
            progress_summary=long_run_summary,
        ),
        latest_message_summary=None,
        projection_health=ProjectionHealth(
            state="ok",
            canonical_last_sequence=3,
            projected_last_sequence=3,
        ),
        next_action_summary=(
            "Wait for the current turn to finish"
            if active
            else "Resolve pending approval"
            if pending_approval_id is not None
            else "Answer pending question"
            if pending_question_id is not None
            else "Inspect failed session"
            if status == "failed"
            else "Send the next prompt"
        ),
    )
