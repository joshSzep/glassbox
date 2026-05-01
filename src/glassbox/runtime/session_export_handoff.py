"""Reviewer handoff summary helpers for portable session exports."""

from collections.abc import Sequence

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.runtime.branch_decision_support import BranchSearchDecisionSupport
from glassbox.runtime.branch_decision_support import (
    derive_branch_search_decision_support,
)
from glassbox.runtime.knowledge_posture import WorkspaceKnowledgePosture
from glassbox.runtime.session_export_models import SessionExportBranchSearchSummary
from glassbox.runtime.session_export_models import SessionExportHandoff
from glassbox.runtime.session_export_models import SessionExportHandoffSummary
from glassbox.runtime.session_export_redaction import RedactionContext
from glassbox.runtime.session_export_redaction import redact_optional_text
from glassbox.runtime.session_export_redaction import redact_text
from glassbox.runtime.session_export_utils import dedupe
from glassbox.runtime.session_export_utils import enum_value
from glassbox.runtime.session_export_utils import message_text
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.task_queries import TaskDetailView


def build_export_handoff(
    snapshot: SessionSnapshotView,
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
    *,
    latest_checkpoint: TaskCheckpointRecord | None,
    exported_by: str | None,
    expected_custodian: str | None,
    note: str | None,
    summary: SessionExportHandoffSummary,
) -> SessionExportHandoff:
    return SessionExportHandoff(
        exported_by=redact_optional_text(exported_by, redaction_context),
        expected_custodian=redact_optional_text(
            expected_custodian,
            redaction_context,
        ),
        note=redact_optional_text(note, redaction_context),
        last_actor_hint=last_actor_hint(events, redaction_context),
        next_action_summary=session_next_action_summary(snapshot),
        pending_approval_id=snapshot.pending_approval_id,
        pending_question_id=snapshot.pending_question_id,
        pending_question_text=redact_optional_text(
            snapshot.pending_question_text,
            redaction_context,
        ),
        session_failure_message=redact_optional_text(
            snapshot.session_failure_message,
            redaction_context,
        ),
        session_failure_retryable=snapshot.session_failure_retryable,
        latest_checkpoint=latest_checkpoint,
        summary=summary,
        historical_only=snapshot.status in {"completed", "failed", "cancelled"},
        live_actionable=snapshot.status
        in {"running", "awaiting_approval", "awaiting_user_input"},
    )


def build_handoff_summary(
    *,
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    compactions: Sequence[ContextCompactionRecord],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    knowledge_posture: WorkspaceKnowledgePosture,
    redaction_context: RedactionContext,
) -> SessionExportHandoffSummary:
    return SessionExportHandoffSummary(
        latest_objective=latest_objective(
            snapshot,
            task_details,
            branch_search_summaries,
            redaction_context,
        ),
        checkpoint_posture=checkpoint_posture(snapshot, redaction_context),
        compaction_posture=compaction_posture(compactions),
        verification_state=verification_state(task_details),
        accepted_risks=accepted_risks_for_handoff(
            task_details,
            compactions,
            branch_search_summaries,
            redaction_context,
        ),
        pending_actions=pending_actions_for_handoff(
            snapshot,
            task_details,
            branch_search_summaries,
            redaction_context,
        ),
        branch_lineage=branch_lineage(
            snapshot,
            branch_search_summaries,
            redaction_context,
        ),
        knowledge_posture=knowledge_posture_summary(knowledge_posture),
        safe_inspection_commands=safe_inspection_commands(
            snapshot,
            task_details,
            branch_search_summaries,
        ),
    )


def latest_objective(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: RedactionContext,
) -> str:
    if snapshot.latest_checkpoint is not None:
        return redact_text(snapshot.latest_checkpoint.objective, redaction_context)
    if task_details:
        latest_task = max(task_details, key=lambda detail: detail.task.updated_at)
        return redact_text(latest_task.task.goal, redaction_context)
    if branch_search_summaries:
        latest_search = max(
            branch_search_summaries,
            key=lambda summary: summary.search.updated_at,
        )
        return redact_text(latest_search.search.objective, redaction_context)
    for message in reversed(snapshot.transcript):
        if enum_value(message.role) != "user":
            continue
        text = message_text(message.parts)
        if text:
            return redact_text(text, redaction_context)
    return "Inspect session state and decide the next safe action."


def checkpoint_posture(
    snapshot: SessionSnapshotView,
    redaction_context: RedactionContext,
) -> str:
    checkpoint = snapshot.latest_checkpoint
    if checkpoint is not None:
        status = checkpoint.verification_status or checkpoint.budget_status or "unknown"
        return redact_text(
            "Latest checkpoint "
            f"{checkpoint.checkpoint_id} covers events "
            f"{checkpoint.source_start_sequence}-{checkpoint.source_end_sequence}; "
            f"status {status}; next action: {checkpoint.next_action}",
            redaction_context,
        )
    absence = snapshot.checkpoint_absence
    if absence is not None:
        return redact_text(
            "No checkpoint: "
            f"{enum_value(absence.reason)} ({absence.severity}); "
            f"{absence.message}; next action: {absence.next_action}",
            redaction_context,
        )
    return (
        "No checkpoint evidence is projected; inspect session status before continuing."
    )


def compaction_posture(compactions: Sequence[ContextCompactionRecord]) -> str:
    if not compactions:
        return "No context compaction artifacts are retained for this session."
    stale_count = sum(
        1 for compaction in compactions if enum_value(compaction.freshness) != "fresh"
    )
    accepted_risk_count = sum(
        compaction.accepted_risk_count for compaction in compactions
    )
    latest = max(compactions, key=lambda compaction: compaction.last_sequence)
    stale_fragment = f"{stale_count} stale" if stale_count else "all fresh"
    risk_fragment = (
        f"; {accepted_risk_count} accepted risk(s)" if accepted_risk_count else ""
    )
    return (
        f"{len(compactions)} retained context compaction(s), {stale_fragment}; "
        f"latest covers events {latest.source_start_sequence}-"
        f"{latest.source_end_sequence} ({enum_value(latest.freshness)})"
        f"{risk_fragment}."
    )


def verification_state(task_details: Sequence[TaskDetailView]) -> str:
    if not task_details:
        return "No task plans are retained, so task verification state is absent."
    total = sum(detail.verification_summary.total_count for detail in task_details)
    if total == 0:
        return (
            f"{len(task_details)} task plan(s) retained with no verification "
            "checks yet."
        )
    passed = sum(detail.verification_summary.passed_count for detail in task_details)
    failed = sum(detail.verification_summary.failed_count for detail in task_details)
    running = sum(detail.verification_summary.running_count for detail in task_details)
    skipped = sum(detail.verification_summary.skipped_count for detail in task_details)
    accepted = sum(
        detail.verification_summary.accepted_risk_count for detail in task_details
    )
    postures = dedupe(
        detail.verification_summary.current_posture for detail in task_details
    )
    return (
        f"{len(task_details)} task plan(s), {total} verification check(s): "
        f"{passed} passed, {failed} failed, {running} running, {skipped} skipped, "
        f"{accepted} accepted risk(s); posture {', '.join(postures)}."
    )


def accepted_risks_for_handoff(
    task_details: Sequence[TaskDetailView],
    compactions: Sequence[ContextCompactionRecord],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: RedactionContext,
) -> list[str]:
    risks: list[str] = []
    for detail in task_details:
        for ledger_entry in detail.verification_ledger:
            risks.extend(ledger_entry.accepted_risks)
            if ledger_entry.residual_risk_reason is not None:
                risks.append(ledger_entry.residual_risk_reason)
    compaction_risk_count = sum(
        compaction.accepted_risk_count for compaction in compactions
    )
    if compaction_risk_count:
        risks.append(
            f"{compaction_risk_count} accepted context compaction risk(s) retained"
        )
    for support in branch_support(branch_search_summaries):
        for candidate in support.candidates:
            risks.extend(candidate.accepted_risks)
    return dedupe(redact_text(risk, redaction_context) for risk in risks if risk)[:20]


def pending_actions_for_handoff(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: RedactionContext,
) -> list[str]:
    actions = [session_next_action_summary(snapshot)]
    if snapshot.pending_approval_id is not None:
        actions.append(f"Inspect pending approval {snapshot.pending_approval_id}.")
    if snapshot.pending_question_text is not None:
        actions.append(f"Answer pending question: {snapshot.pending_question_text}")
    if snapshot.session_failure_message is not None:
        actions.append(f"Inspect session failure: {snapshot.session_failure_message}")
    if snapshot.latest_checkpoint is not None:
        actions.append(snapshot.latest_checkpoint.next_action)
    for detail in sorted(
        task_details,
        key=lambda item: item.task.updated_at,
        reverse=True,
    )[:3]:
        actions.append(detail.task.next_action_summary)
    for support in branch_support(branch_search_summaries):
        for candidate in support.candidates:
            if candidate.recommended_follow_up_action:
                actions.append(candidate.recommended_follow_up_action)
    return dedupe(
        redact_text(action, redaction_context) for action in actions if action
    )[:20]


def branch_lineage(
    snapshot: SessionSnapshotView,
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
    redaction_context: RedactionContext,
) -> str:
    if snapshot.parent_session_id is not None:
        lineage = (
            f"Branch session from parent {snapshot.parent_session_id}"
            f" at sequence {snapshot.forked_from_sequence or 'unknown'}"
        )
        if snapshot.branch_label:
            lineage = f"{lineage} ({snapshot.branch_label})"
    else:
        lineage = "Root session"
    if snapshot.child_sessions:
        lineage = f"{lineage}; {len(snapshot.child_sessions)} child session(s)"
    if snapshot.can_fork:
        lineage = (
            f"{lineage}; forkable at sequence "
            f"{snapshot.latest_fork_point_sequence or 'unknown'}"
        )
    elif snapshot.fork_blocked_reason:
        lineage = f"{lineage}; fork blocked: {snapshot.fork_blocked_reason}"
    if branch_search_summaries:
        selected_count = sum(
            1
            for summary in branch_search_summaries
            if summary.search.selected_candidate_id is not None
        )
        lineage = (
            f"{lineage}; {len(branch_search_summaries)} branch search(es), "
            f"{selected_count} with selected candidate"
        )
    return redact_text(lineage, redaction_context)


def knowledge_posture_summary(posture: WorkspaceKnowledgePosture) -> str:
    cue_fragments = [f"{cue.key}={cue.status}" for cue in posture.cues[:6]]
    return f"Overall {posture.overall_status}; " + ", ".join(cue_fragments)


def safe_inspection_commands(
    snapshot: SessionSnapshotView,
    task_details: Sequence[TaskDetailView],
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
) -> list[str]:
    commands = [
        f"glassbox session status {snapshot.session_id} --cwd .",
        f"glassbox session compactions {snapshot.session_id} --cwd .",
        "glassbox observability status --cwd .",
        "glassbox eval audit --cwd .",
    ]
    commands.extend(
        f"glassbox task show {detail.task.task_id} --cwd ."
        for detail in sorted(
            task_details,
            key=lambda item: item.task.updated_at,
            reverse=True,
        )[:3]
    )
    commands.extend(
        f"glassbox branch-search show {summary.search.search_id} --cwd ."
        for summary in branch_search_summaries[:3]
    )
    return dedupe(commands)[:20]


def branch_support(
    branch_search_summaries: Sequence[SessionExportBranchSearchSummary],
) -> list[BranchSearchDecisionSupport]:
    return [
        derive_branch_search_decision_support(
            search=summary.search,
            candidates=summary.candidates,
        )
        for summary in branch_search_summaries
    ]


def session_next_action_summary(snapshot: SessionSnapshotView) -> str:
    if snapshot.projection_health.degraded:
        return "Rebuild derived projections from canonical events"
    if snapshot.budget_posture is not None:
        budget_action = budget_export_next_action(snapshot.budget_posture)
        if budget_action is not None:
            return budget_action
    if snapshot.status == "awaiting_user_input":
        return "Answer pending question"
    if snapshot.status == "awaiting_approval":
        return "Resolve pending approval"
    if snapshot.status == "running":
        if snapshot.current_turn_id is None:
            return "Send the next prompt or attach to continue live work"
        return "Wait for the current turn to finish or attach for live updates"
    if snapshot.status == "failed":
        return "Review failed session and decide whether to fork or retry"
    if snapshot.status == "completed":
        return "Inspect historical session or fork from a stable turn"
    return "Inspect session state"


def budget_export_next_action(budget_posture) -> str | None:
    if budget_posture.last_reason is None:
        return None
    if budget_posture.last_reason == "budget_exhausted":
        return "Review budget exhaustion and choose a smaller next step or override"
    if budget_posture.last_reason == "policy_blocked":
        return "Review policy block before continuing"
    if budget_posture.last_reason == "verification_failed":
        return "Review failed verification before continuing"
    if budget_posture.last_reason == "approval_required":
        return "Resolve pending approval"
    return None


def last_actor_hint(
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
) -> str | None:
    for event in reversed(events):
        if isinstance(event.payload, ApprovalResolved):
            return redact_text(event.payload.decided_by, redaction_context)
    return None
