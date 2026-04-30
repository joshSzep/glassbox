"""Pure helpers for building session query read models."""

from collections.abc import Sequence
from datetime import datetime

from glassbox.core.events import EventEnvelope
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ResumeOutcomeRecorded
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import TurnCancelled
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import PolicyActivitySummary
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.models import TurnRecoveryPosture
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ResumeOutcomeStatus
from glassbox.core.types import TurnRecoveryState
from glassbox.runtime.session_query_models import BranchableTurnView
from glassbox.services import SessionRepository


def child_counts_by_parent(records: Sequence[SessionRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if record.parent_session_id is None:
            continue
        parent_session_id = str(record.parent_session_id)
        counts[parent_session_id] = counts.get(parent_session_id, 0) + 1
    return counts


def branchable_turns_from_events(
    events: Sequence[EventEnvelope],
) -> list[BranchableTurnView]:
    user_messages_by_id: dict[str, str] = {}
    trigger_message_ids_by_turn: dict[str, str] = {}
    branchable_turns: list[BranchableTurnView] = []

    for event in events:
        if isinstance(event.payload, UserMessageReceived):
            user_messages_by_id[str(event.payload.message_id)] = event.payload.text
            continue

        if isinstance(event.payload, TurnStarted):
            trigger_message_ids_by_turn[str(event.payload.turn_id)] = str(
                event.payload.trigger_message_id
            )
            continue

        if not isinstance(event.payload, TurnCompleted):
            continue
        if event.payload.outcome != "completed":
            continue

        turn_id = str(event.payload.turn_id)
        trigger_message_id = trigger_message_ids_by_turn.get(turn_id)
        label = (
            user_messages_by_id.get(trigger_message_id or "") or f"Turn {turn_id[:8]}"
        )
        branchable_turns.append(
            BranchableTurnView(
                turn_id=event.payload.turn_id,
                sequence=event.sequence,
                created_at=event.created_at,
                label=label,
            )
        )

    branchable_turns.sort(key=lambda turn: turn.sequence, reverse=True)
    return branchable_turns


def dashboard_url_from_events(events: Sequence[EventEnvelope]) -> str | None:
    for event in events:
        if isinstance(event.payload, SessionStarted):
            return event.payload.dashboard_url
    return None


def fork_capability(
    session_repository: SessionRepository,
    session_id: SessionId,
) -> tuple[bool, TurnId | None, int | None, str | None]:
    try:
        fork_point = session_repository.resolve_fork_point(session_id)
    except ValueError as exc:
        return False, None, None, str(exc)

    return True, fork_point.turn_id, fork_point.sequence, None


def latest_message_summary(transcript: Sequence[TranscriptMessage]) -> str | None:
    if not transcript:
        return None

    latest_message = transcript[-1]
    text = " ".join(
        part.text.strip().replace("\n", " ")
        for part in latest_message.parts
        if part.text.strip()
    ).strip()
    if not text:
        return latest_message.role
    return f"{latest_message.role}: {text}"


def latest_session_failure(events: Sequence[EventEnvelope]) -> SessionFailed | None:
    for event in reversed(events):
        if isinstance(event.payload, SessionFailed):
            return event.payload
    return None


def pending_question_text_from_events(
    events: Sequence[EventEnvelope],
    pending_question_id,
) -> str | None:
    if pending_question_id is None:
        return None

    pending_question_id_text = str(pending_question_id)
    for event in reversed(events):
        if not isinstance(event.payload, UserQuestionAsked):
            continue
        if str(event.payload.question_id) != pending_question_id_text:
            continue
        return event.payload.question
    return None


def next_action_summary(
    status: str,
    *,
    projection_health: ProjectionHealth,
    pending_question_text: str | None,
    session_failure: SessionFailed | None,
    current_turn_id,
    turn_recovery_posture: TurnRecoveryPosture | None = None,
    budget_posture: AutonomyBudgetPostureRecord | None = None,
) -> str:
    if projection_health.degraded:
        return "Rebuild derived projections from canonical events"

    if turn_recovery_posture is not None and turn_recovery_posture.state in {
        TurnRecoveryState.INCOMPLETE,
        TurnRecoveryState.RECOVERABLE,
        TurnRecoveryState.ABANDONED,
        TurnRecoveryState.NON_RESUMABLE,
    }:
        return turn_recovery_posture.next_action

    if budget_posture is not None:
        budget_action = _budget_next_action_summary(budget_posture)
        if budget_action is not None:
            return budget_action

    if status == "awaiting_user_input":
        if pending_question_text is not None:
            return f"Answer pending question: {pending_question_text}"
        return "Answer pending question"

    if status == "awaiting_approval":
        return "Resolve pending approval"

    if status == "running":
        if current_turn_id is not None:
            return "Wait for the current turn to finish"
        return "Send the next prompt"

    if status == "failed":
        if session_failure is not None:
            return f"Review failure: {session_failure.error_message}"
        return "Review failed session"

    if status == "completed":
        return "Inspect completed session"

    if status == "cancelled":
        return "Inspect cancelled session"

    return "Inspect session"


def turn_recovery_posture_from_events(
    events: Sequence[EventEnvelope],
    *,
    current_turn_id: TurnId | None,
) -> TurnRecoveryPosture | None:
    """Derive the latest turn recovery posture from canonical events."""

    latest_turn_id: TurnId | None = None
    terminal_turn_ids: set[str] = set()

    for event in events:
        payload = event.payload
        if isinstance(payload, TurnStarted):
            latest_turn_id = payload.turn_id
        elif isinstance(payload, TurnCompleted | TurnFailed | TurnCancelled):
            terminal_turn_ids.add(str(payload.turn_id))

    target_turn_id = (
        current_turn_id or _latest_recovery_turn_id(events) or latest_turn_id
    )
    if target_turn_id is None:
        return None

    target_turn_id_text = str(target_turn_id)
    recovery_event = _latest_recovery_event_for_turn(events, target_turn_id_text)
    if recovery_event is not None:
        payload = recovery_event.payload
        if isinstance(payload, RecoveryDecisionRecorded):
            return _posture_from_recovery_decision(payload, recovery_event.event_type)
        if isinstance(payload, ResumeOutcomeRecorded):
            return _posture_from_resume_outcome(payload, recovery_event.event_type)

    if current_turn_id is not None and target_turn_id_text == str(current_turn_id):
        return TurnRecoveryPosture(
            turn_id=current_turn_id,
            state=TurnRecoveryState.ACTIVE,
            safe_to_resume=None,
            reason="turn has no terminal event yet",
            next_action=(
                "Wait for the current turn to finish, or inspect runtime owner "
                "before attempting recovery"
            ),
            source_event_type="TurnStarted",
        )

    if target_turn_id_text not in terminal_turn_ids:
        return TurnRecoveryPosture(
            turn_id=target_turn_id,
            state=TurnRecoveryState.INCOMPLETE,
            safe_to_resume=False,
            reason="turn has no terminal event in canonical events",
            next_action=(
                "Inspect runtime owner; if no live owner exists, resume will "
                "record a recovery decision instead of continuing the stream"
            ),
            source_event_type="TurnStarted",
        )

    return None


def _latest_recovery_turn_id(events: Sequence[EventEnvelope]) -> TurnId | None:
    for event in reversed(events):
        payload = event.payload
        if isinstance(payload, RecoveryDecisionRecorded | ResumeOutcomeRecorded):
            if payload.turn_id is not None:
                return payload.turn_id
    return None


def _latest_recovery_event_for_turn(
    events: Sequence[EventEnvelope],
    turn_id: str,
) -> EventEnvelope | None:
    for event in reversed(events):
        payload = event.payload
        if not isinstance(payload, RecoveryDecisionRecorded | ResumeOutcomeRecorded):
            continue
        if payload.turn_id is not None and str(payload.turn_id) == turn_id:
            return event
    return None


def _posture_from_recovery_decision(
    payload: RecoveryDecisionRecorded,
    source_event_type: str,
) -> TurnRecoveryPosture:
    state = TurnRecoveryState.RECOVERABLE
    if payload.decision == RecoveryDecision.ABANDON:
        state = TurnRecoveryState.ABANDONED
    elif payload.decision == RecoveryDecision.NON_RESUMABLE:
        state = TurnRecoveryState.NON_RESUMABLE

    assert payload.turn_id is not None
    return TurnRecoveryPosture(
        turn_id=payload.turn_id,
        state=state,
        safe_to_resume=payload.safe_to_resume,
        reason=payload.reason,
        next_action=payload.next_action,
        source_event_type=source_event_type,
        recovery_decision_id=str(payload.recovery_decision_id),
    )


def _posture_from_resume_outcome(
    payload: ResumeOutcomeRecorded,
    source_event_type: str,
) -> TurnRecoveryPosture:
    state = TurnRecoveryState.RECOVERABLE
    if payload.outcome == ResumeOutcomeStatus.RESUMED:
        state = TurnRecoveryState.RESUMED
    elif payload.outcome == ResumeOutcomeStatus.REJECTED_NON_RESUMABLE:
        state = TurnRecoveryState.NON_RESUMABLE

    assert payload.turn_id is not None
    return TurnRecoveryPosture(
        turn_id=payload.turn_id,
        state=state,
        safe_to_resume=payload.outcome == ResumeOutcomeStatus.RESUMED,
        reason=payload.summary,
        next_action=_next_action_for_resume_outcome(payload.outcome),
        source_event_type=source_event_type,
        recovery_decision_id=(
            str(payload.recovery_decision_id)
            if payload.recovery_decision_id is not None
            else None
        ),
    )


def _next_action_for_resume_outcome(outcome: ResumeOutcomeStatus) -> str:
    if outcome == ResumeOutcomeStatus.RESUMED:
        return "Inspect resumed turn output"
    if outcome == ResumeOutcomeStatus.REJECTED_NON_RESUMABLE:
        return "Retry with a new prompt, fork from a completed turn, or abandon"
    if outcome == ResumeOutcomeStatus.REJECTED_STALE:
        return "Refresh status and inspect the latest recovery decision"
    return "Inspect recovery failure before retrying"


def _budget_next_action_summary(
    budget_posture: AutonomyBudgetPostureRecord,
) -> str | None:
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


def session_status(record: SessionRecord, state: SessionState | None) -> str:
    return state.status if state is not None else record.status


def last_sequence(record: SessionRecord, state: SessionState | None) -> int:
    return state.last_sequence if state is not None else record.last_sequence


def effective_current_turn_id(
    current_turn_id: TurnId | None,
    status: str,
    approvals: Sequence[ApprovalRecord],
) -> TurnId | None:
    if current_turn_id is not None:
        return current_turn_id
    if status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def find_turn_metrics(
    turn_metrics: Sequence[TurnMetricsRecord],
    turn_id: TurnId | None,
) -> TurnMetricsRecord | None:
    if turn_id is None:
        return None
    for metrics in turn_metrics:
        if metrics.turn_id == turn_id:
            return metrics
    return None


def recent_tool_calls(
    tool_calls: Sequence[ToolCallRecord],
    *,
    limit: int,
) -> list[ToolCallRecord]:
    def sort_key(tool_call: ToolCallRecord) -> datetime:
        return tool_call.completed_at or tool_call.started_at or datetime.min

    return sorted(tool_calls, key=sort_key, reverse=True)[:limit]


def latest_policy_turn_id(tool_calls: Sequence[ToolCallRecord]) -> TurnId | None:
    recent_calls = recent_tool_calls(tool_calls, limit=1)
    if not recent_calls:
        return None
    return recent_calls[0].turn_id


def summarize_policy_activity(
    tool_calls: Sequence[ToolCallRecord],
    *,
    turn_id: TurnId | None = None,
) -> PolicyActivitySummary:
    summary = PolicyActivitySummary()
    highest_rank = -1
    highest_risk_level = None
    risk_ranks = {
        "read_only": 0,
        "workspace_write": 1,
        "command": 2,
    }

    for tool_call in tool_calls:
        if turn_id is not None and tool_call.turn_id != turn_id:
            continue
        if tool_call.policy_outcome is None or tool_call.policy_risk_level is None:
            continue

        summary.total_decisions += 1
        if tool_call.policy_outcome == "allow":
            summary.allow_count += 1
        elif tool_call.policy_outcome == "approve":
            summary.approve_count += 1
        elif tool_call.policy_outcome == "deny":
            summary.deny_count += 1
        elif tool_call.policy_outcome == "blocked":
            summary.blocked_count += 1

        if tool_call.policy_risk_level == "read_only":
            summary.read_only_count += 1
        elif tool_call.policy_risk_level == "workspace_write":
            summary.workspace_write_count += 1
        elif tool_call.policy_risk_level == "command":
            summary.command_count += 1

        current_rank = risk_ranks.get(tool_call.policy_risk_level, -1)
        if current_rank > highest_rank:
            highest_rank = current_rank
            highest_risk_level = tool_call.policy_risk_level

    summary.highest_risk_level = highest_risk_level
    return summary
