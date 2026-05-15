"""Task-level v17 handoff readiness derivation."""

from collections.abc import Sequence

from glassbox.core import HandoffEvidenceFreshness
from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReason
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffReadinessState
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import RepositoryIntelligenceConfidence
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskId
from glassbox.core import TaskPlanStatus
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskQueryService


class TaskHandoffReadinessService:
    """Read-only service for durable task-plan handoff readiness."""

    def __init__(self, query_service: TaskQueryService) -> None:
        self._query_service = query_service

    def preview(
        self,
        task_id: TaskId,
        *,
        intent: HandoffIntent = HandoffIntent.CONTINUE_WORK,
    ) -> HandoffReadiness:
        detail = self._query_service.get_task_detail(task_id)
        return derive_task_handoff_readiness(detail, intent=intent)


def derive_task_handoff_readiness(
    detail: TaskDetailView,
    *,
    intent: HandoffIntent = HandoffIntent.CONTINUE_WORK,
) -> HandoffReadiness:
    """Derive advisory readiness for handing off a durable task plan."""

    task = detail.task
    reasons: list[HandoffReadinessReason] = []
    supporting_evidence = _supporting_evidence(detail)
    missing_evidence = _missing_evidence(detail, intent=intent)
    stale_evidence = _stale_evidence(detail)
    local_only_evidence = _local_only_evidence(detail)
    accepted_risks = _accepted_risks(detail)
    limitations = _limitations(
        detail,
        intent=intent,
        local_only_evidence=local_only_evidence,
        accepted_risks=accepted_risks,
    )

    reasons.extend(_status_reasons(detail))
    state = _task_handoff_state(
        detail,
        intent=intent,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        accepted_risks=accepted_risks,
    )

    return HandoffReadiness(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.TASK,
            primary_id=str(task.task_id),
            identifiers={"session_id": str(task.session_id)},
            label=task.title,
        ),
        intent=intent,
        state=state,
        confidence=_confidence_for_state(state),
        freshness=_freshness_for_state(state),
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        accepted_risks=accepted_risks,
        limitations=limitations,
        safe_first_commands=_safe_first_commands(task.task_id, task.session_id),
        non_claims=[
            "task handoff readiness is advisory local posture, not approval",
            (
                "task handoff readiness does not continue, approve, answer, "
                "stage, commit, push, merge, deploy, or publish"
            ),
            (
                "task readiness summarizes task-specific continuation posture "
                "and links back to session evidence"
            ),
            (
                "verification, checkpoint, budget, and continuation-window "
                "posture remain bounded by retained local evidence"
            ),
        ],
    )


def _task_handoff_state(
    detail: TaskDetailView,
    *,
    intent: HandoffIntent,
    missing_evidence: Sequence[NextActionEvidenceRef],
    stale_evidence: Sequence[NextActionEvidenceRef],
    local_only_evidence: Sequence[HandoffReadinessReason],
    accepted_risks: Sequence[HandoffReadinessReason],
) -> HandoffReadinessState:
    task = detail.task
    if task.blocked_reason == TaskBlockedReason.AWAITING_APPROVAL:
        return HandoffReadinessState.AWAITING_APPROVAL
    if task.blocked_reason == TaskBlockedReason.AWAITING_USER_INPUT:
        return HandoffReadinessState.AWAITING_ANSWER
    if task.status == TaskPlanStatus.FAILED:
        return HandoffReadinessState.FAILED_NEEDS_TRIAGE
    if task.blocked_reason == TaskBlockedReason.VERIFICATION_FAILED:
        return HandoffReadinessState.NEEDS_VERIFICATION
    if stale_evidence:
        return HandoffReadinessState.STALE_EVIDENCE
    if detail.verification_summary.failed_count or detail.repair_history.status in {
        "failed",
        "regressed",
    }:
        return HandoffReadinessState.NEEDS_VERIFICATION
    if task.blocked_reason is not None:
        return HandoffReadinessState.BLOCKED
    if (
        task.status
        in {
            TaskPlanStatus.COMPLETED,
            TaskPlanStatus.CANCELLED,
            TaskPlanStatus.ABANDONED,
        }
        and intent == HandoffIntent.CONTINUE_WORK
    ):
        return HandoffReadinessState.HISTORICAL_ONLY
    if task.status in {TaskPlanStatus.PROPOSED, TaskPlanStatus.PAUSED}:
        return HandoffReadinessState.NEEDS_CONTEXT
    if (
        intent == HandoffIntent.VERIFICATION_NEEDED
        and detail.verification_summary.total_count == 0
    ):
        return HandoffReadinessState.NEEDS_VERIFICATION
    if missing_evidence and intent in {
        HandoffIntent.CONTINUE_WORK,
        HandoffIntent.FUTURE_SELF,
        HandoffIntent.FORK_RECOMMENDED,
    }:
        return HandoffReadinessState.NEEDS_CONTEXT
    if accepted_risks:
        return HandoffReadinessState.ACCEPTED_WITH_RISK
    if local_only_evidence and intent != HandoffIntent.FUTURE_SELF:
        return HandoffReadinessState.LOCAL_ONLY_EVIDENCE
    return HandoffReadinessState.READY


def _supporting_evidence(detail: TaskDetailView) -> list[NextActionEvidenceRef]:
    task = detail.task
    evidence = [
        _evidence(
            NextActionEvidenceKind.EVENT,
            str(task.task_id),
            f"Task objective: {task.goal}",
        ),
        _evidence(
            NextActionEvidenceKind.EVENT,
            f"{task.task_id}:steps",
            f"{len(detail.steps)} projected task step(s)",
        ),
    ]
    if detail.verification_summary.total_count:
        evidence.append(
            _evidence(
                NextActionEvidenceKind.VERIFICATION,
                str(task.task_id),
                (
                    f"{detail.verification_summary.passed_count} passed, "
                    f"{detail.verification_summary.failed_count} failed, "
                    f"{detail.verification_summary.running_count} running "
                    "verification ledger item(s)"
                ),
                freshness=detail.verification_summary.current_posture,
            )
        )
    if detail.last_known_good is not None:
        evidence.append(
            _evidence(
                NextActionEvidenceKind.VERIFICATION,
                str(detail.last_known_good.verification_id),
                f"Last known good: {detail.last_known_good.check_name}",
                freshness=detail.last_known_good.evidence_status,
            )
        )
    return evidence


def _missing_evidence(
    detail: TaskDetailView,
    *,
    intent: HandoffIntent,
) -> list[NextActionEvidenceRef]:
    missing: list[NextActionEvidenceRef] = []
    if not detail.steps:
        missing.append(
            _evidence(
                NextActionEvidenceKind.EVENT,
                f"{detail.task.task_id}:steps",
                "Task has no projected plan steps.",
                freshness="missing",
            )
        )
    if (
        intent
        in {
            HandoffIntent.CONTINUE_WORK,
            HandoffIntent.VERIFICATION_NEEDED,
            HandoffIntent.FUTURE_SELF,
            HandoffIntent.FORK_RECOMMENDED,
        }
        and detail.verification_summary.total_count == 0
    ):
        missing.append(
            _evidence(
                NextActionEvidenceKind.VERIFICATION,
                f"{detail.task.task_id}:verification",
                "Task has no retained verification ledger entries.",
                freshness="missing",
            )
        )
    if (
        detail.task.current_step_id is None
        and detail.task.status == TaskPlanStatus.ACTIVE
    ):
        missing.append(
            _evidence(
                NextActionEvidenceKind.EVENT,
                f"{detail.task.task_id}:current-step",
                "Active task has no current step marker.",
                freshness="missing",
            )
        )
    return missing


def _stale_evidence(detail: TaskDetailView) -> list[NextActionEvidenceRef]:
    stale: list[NextActionEvidenceRef] = []
    if detail.verification_drift.posture == "stale":
        stale.append(
            _evidence(
                NextActionEvidenceKind.VERIFICATION,
                f"{detail.task.task_id}:verification-drift",
                detail.verification_drift.reason,
                freshness="stale",
            )
        )
    if (
        detail.last_known_good is not None
        and detail.last_known_good.evidence_status == "stale"
    ):
        stale.append(
            _evidence(
                NextActionEvidenceKind.VERIFICATION,
                str(detail.last_known_good.verification_id),
                "Last known good verification is stale for current workspace paths.",
                freshness="stale",
            )
        )
    return stale


def _local_only_evidence(detail: TaskDetailView) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if detail.last_known_good is not None and detail.last_known_good.artifact_id:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Last-known-good verification artifact remains managed local "
                    "evidence and may not travel in a portable handoff package."
                ),
                portable=False,
            )
        )
    if detail.last_known_good is not None and detail.last_known_good.checkpoint_id:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Checkpoint context links task continuation to local session "
                    "evidence; inspect the source session before continuing."
                ),
                portable=False,
            )
        )
    return reasons


def _accepted_risks(detail: TaskDetailView) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    for item in detail.verification_ledger:
        if item.accepted_risk_count:
            reasons.append(
                HandoffReadinessReason(
                    kind=HandoffReadinessReasonKind.ACCEPTED_RISK,
                    summary=(
                        f"{item.check_name} carries {item.accepted_risk_count} "
                        "accepted risk item(s)."
                    ),
                    limitation=item.residual_risk_reason,
                )
            )
    return reasons[:50]


def _status_reasons(detail: TaskDetailView) -> list[HandoffReadinessReason]:
    task = detail.task
    reasons: list[HandoffReadinessReason] = []
    if task.blocked_reason is not None:
        reasons.append(
            HandoffReadinessReason(
                kind=_blocked_reason_kind(task.blocked_reason),
                summary=task.blocked_detail
                or f"Task is blocked by {task.blocked_reason.value}.",
            )
        )
    if task.status == TaskPlanStatus.FAILED:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE,
                summary=(
                    "Task status is failed; triage failure evidence before handoff."
                ),
            )
        )
    if detail.verification_summary.failed_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MISSING_EVIDENCE,
                summary=(
                    f"{detail.verification_summary.failed_count} verification "
                    "ledger item(s) failed and need follow-up."
                ),
            )
        )
    return reasons


def _blocked_reason_kind(
    reason: TaskBlockedReason,
) -> HandoffReadinessReasonKind:
    if reason == TaskBlockedReason.AWAITING_APPROVAL:
        return HandoffReadinessReasonKind.POLICY_BLOCKER
    if reason == TaskBlockedReason.AWAITING_USER_INPUT:
        return HandoffReadinessReasonKind.MISSING_EVIDENCE
    if reason == TaskBlockedReason.VERIFICATION_FAILED:
        return HandoffReadinessReasonKind.MISSING_EVIDENCE
    return HandoffReadinessReasonKind.PACKAGE_LIMITATION


def _limitations(
    detail: TaskDetailView,
    *,
    intent: HandoffIntent,
    local_only_evidence: Sequence[HandoffReadinessReason],
    accepted_risks: Sequence[HandoffReadinessReason],
) -> list[str]:
    task = detail.task
    limitations: list[str] = []
    if task.status == TaskPlanStatus.PAUSED:
        limitations.append(
            "Task is paused; inspect checkpoint, pause-window, and queue state before "
            "choosing continuation."
        )
    if task.status in {
        TaskPlanStatus.COMPLETED,
        TaskPlanStatus.CANCELLED,
        TaskPlanStatus.ABANDONED,
    }:
        limitations.append(
            f"Task is {task.status.value}; continuation requires an explicit fork or "
            "new local workflow."
        )
    if detail.verification_drift.posture != "not_assessed":
        limitations.append(f"Verification drift: {detail.verification_drift.reason}")
    if detail.repair_history.status not in {"clean", "no_verification"}:
        limitations.append(
            f"Verify-repair posture is {detail.repair_history.status}; inspect task "
            "events before relying on the task."
        )
    if detail.verification_summary.accepted_risk_count or accepted_risks:
        limitations.append(
            "Accepted verification risk must stay visible to the recipient."
        )
    if local_only_evidence:
        limitations.append(
            "Some task evidence is local-only and cannot be verified from a portable "
            "package alone."
        )
    if intent == HandoffIntent.REVIEW_ONLY:
        limitations.append(
            "Review-only task handoff does not imply continuation authority."
        )
    return list(dict.fromkeys(limitations))[:50]


def _safe_first_commands(
    task_id: TaskId,
    session_id,
) -> list[HandoffSafeCommand]:
    return [
        HandoffSafeCommand(
            command=["glassbox", "task", "show", str(task_id), "--cwd", "."],
            display=f"glassbox task show {task_id} --cwd .",
            purpose=(
                "Inspect projected task plan, steps, verification, and repair posture."
            ),
        ),
        HandoffSafeCommand(
            command=["glassbox", "task", "events", str(task_id), "--cwd", "."],
            display=f"glassbox task events {task_id} --cwd .",
            purpose="Inspect canonical task events before continuing or forking.",
        ),
        HandoffSafeCommand(
            command=[
                "glassbox",
                "session",
                "status",
                str(session_id),
                "--cwd",
                ".",
            ],
            display=f"glassbox session status {session_id} --cwd .",
            purpose="Inspect source session posture before acting on the task.",
        ),
        HandoffSafeCommand(
            command=["glassbox", "job", "list", "--cwd", "."],
            display="glassbox job list --cwd .",
            purpose=(
                "Inspect background jobs, budgets, and continuation-window posture."
            ),
        ),
        HandoffSafeCommand(
            command=["glassbox", "eval", "audit", "--cwd", "."],
            display="glassbox eval audit --cwd .",
            purpose=(
                "Inspect retained verification and eval posture without running checks."
            ),
        ),
    ]


def _freshness_for_state(state: HandoffReadinessState) -> HandoffEvidenceFreshness:
    if state == HandoffReadinessState.STALE_EVIDENCE:
        return HandoffEvidenceFreshness.STALE
    if state in {
        HandoffReadinessState.NEEDS_CONTEXT,
        HandoffReadinessState.NEEDS_VERIFICATION,
    }:
        return HandoffEvidenceFreshness.MISSING
    if state in {
        HandoffReadinessState.BLOCKED,
        HandoffReadinessState.FAILED_NEEDS_TRIAGE,
    }:
        return HandoffEvidenceFreshness.DEGRADED
    return HandoffEvidenceFreshness.FRESH


def _confidence_for_state(
    state: HandoffReadinessState,
) -> RepositoryIntelligenceConfidence:
    if state in {HandoffReadinessState.READY, HandoffReadinessState.HISTORICAL_ONLY}:
        return RepositoryIntelligenceConfidence.HIGH
    if state in {
        HandoffReadinessState.LOCAL_ONLY_EVIDENCE,
        HandoffReadinessState.STALE_EVIDENCE,
        HandoffReadinessState.ACCEPTED_WITH_RISK,
    }:
        return RepositoryIntelligenceConfidence.MEDIUM
    if state in {
        HandoffReadinessState.BLOCKED,
        HandoffReadinessState.FAILED_NEEDS_TRIAGE,
    }:
        return RepositoryIntelligenceConfidence.LOW
    return RepositoryIntelligenceConfidence.UNKNOWN


def _evidence(
    kind: NextActionEvidenceKind,
    ref_id: str,
    summary: str,
    *,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    return NextActionEvidenceRef(
        kind=kind,
        ref_id=ref_id,
        summary=summary,
        freshness=freshness,
    )


__all__ = [
    "TaskHandoffReadinessService",
    "derive_task_handoff_readiness",
]
