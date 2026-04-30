"""Normalization and mismatch comparison helpers for deterministic replay."""

from collections.abc import Sequence
from typing import Any
from typing import cast

from glassbox.core.events import CancellationAcknowledged
from glassbox.core.events import CancellationFailed
from glassbox.core.events import CancellationRequested
from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import EventEnvelope
from glassbox.core.events import LongRunPhaseChanged
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ResumeOutcomeRecorded
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import ToolExecutionCancelled
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCancelled
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_fingerprints import fingerprint_replay_payload
from glassbox.runtime.replay_models import ReplayApprovalSnapshot
from glassbox.runtime.replay_models import ReplayBudgetSnapshot
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayCancellationSnapshot
from glassbox.runtime.replay_models import ReplayFinalStateSnapshot
from glassbox.runtime.replay_models import ReplayLineageSnapshot
from glassbox.runtime.replay_models import ReplayLongRunEventSnapshot
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.replay_models import ReplayQuestionSnapshot
from glassbox.runtime.replay_models import ReplayTaskPlanSnapshot
from glassbox.runtime.replay_models import ReplayTaskStepSnapshot
from glassbox.runtime.replay_models import ReplayTaskVerificationSnapshot
from glassbox.runtime.replay_models import ReplayToolCallSnapshot
from glassbox.runtime.replay_models import ReplayTranscriptMessage
from glassbox.runtime.replay_models import ReplayTranscriptPart
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.services import SessionRepository


def normalize_session(
    session_id: SessionId,
    repository: SessionRepository,
    events: Sequence[EventEnvelope],
) -> ReplayNormalizedSession:
    session_record = repository.get_session(session_id)
    if session_record is None:
        raise ReplayFailure(f"unknown replay session {session_id}")
    session_state = repository.get_session_state(session_id)
    if session_state is None:
        raise ReplayFailure(f"unknown session state for replay session {session_id}")
    transcript_messages = repository.list_transcript_messages(session_id)
    imported_message_ids = {
        payload.message_id
        for event in events
        if isinstance((payload := event.payload), TranscriptMessageImported)
    }
    normalized_transcript = [
        normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
    ]
    inherited_transcript = [
        normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
        if message.message_id in imported_message_ids
    ]
    post_fork_transcript = [
        normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
        if message.message_id not in imported_message_ids
    ]

    return ReplayNormalizedSession(
        transcript=normalized_transcript,
        lineage=normalize_lineage(session_record),
        inherited_transcript=inherited_transcript,
        post_fork_transcript=post_fork_transcript,
        tool_calls=[
            ReplayToolCallSnapshot(
                tool_name=tool_call.tool_name,
                status=enum_value(tool_call.status),
                summary=tool_call.summary,
            )
            for tool_call in repository.list_tool_calls(session_id)
        ],
        approvals=[
            ReplayApprovalSnapshot(
                subject=approval.subject,
                reason=approval.reason,
                status=enum_value(approval.status),
                decided_by=approval.decided_by,
            )
            for approval in repository.list_approvals(session_id)
        ],
        questions=normalize_questions(events),
        cancellations=normalize_cancellations(events),
        task_plans=normalize_task_plans(session_id, repository),
        budget_posture=normalize_budget_posture(session_id, repository),
        long_run_events=normalize_long_run_events(events),
        event_families=[
            event.event_type
            for event in events
            if event.event_type != "ReplayArtifactRecorded"
        ],
        final_state=ReplayFinalStateSnapshot(
            status=enum_value(session_state.status),
            has_active_turn=session_state.current_turn_id is not None,
            has_pending_approval=session_state.pending_approval_id is not None,
            has_pending_question=session_state.pending_question_id is not None,
        ),
    )


def normalize_questions(
    events: Sequence[EventEnvelope],
) -> list[ReplayQuestionSnapshot]:
    questions: list[ReplayQuestionSnapshot] = []
    question_indexes: dict[str, int] = {}
    for event in events:
        payload = event.payload
        if isinstance(payload, UserQuestionAsked):
            question_indexes[str(payload.question_id)] = len(questions)
            questions.append(ReplayQuestionSnapshot(question=payload.question))
            continue
        if not isinstance(payload, UserAnswerProvided):
            continue
        question_index = question_indexes.get(str(payload.question_id))
        if question_index is None:
            questions.append(ReplayQuestionSnapshot(question="", answer=payload.answer))
            continue
        questions[question_index].answer = payload.answer
    return questions


def normalize_cancellations(
    events: Sequence[EventEnvelope],
) -> list[ReplayCancellationSnapshot]:
    cancellations: list[ReplayCancellationSnapshot] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, CancellationRequested):
            cancellations.append(
                ReplayCancellationSnapshot(
                    turn_id=str(payload.turn_id),
                    event="requested",
                    reason=payload.reason,
                )
            )
            continue
        if isinstance(payload, CancellationAcknowledged):
            cancellations.append(
                ReplayCancellationSnapshot(
                    turn_id=str(payload.turn_id),
                    event="acknowledged",
                    reason="repeated" if payload.repeated else None,
                )
            )
            continue
        if isinstance(payload, TurnCancelled):
            cancellations.append(
                ReplayCancellationSnapshot(
                    turn_id=str(payload.turn_id),
                    event="turn_cancelled",
                    reason=payload.reason,
                    stage=payload.stage,
                )
            )
            continue
        if isinstance(payload, ToolExecutionCancelled):
            cancellations.append(
                ReplayCancellationSnapshot(
                    turn_id=str(payload.turn_id),
                    event="tool_cancelled",
                    summary=payload.summary,
                )
            )
            continue
        if isinstance(payload, CancellationFailed):
            if payload.turn_id is None:
                continue
            cancellations.append(
                ReplayCancellationSnapshot(
                    turn_id=str(payload.turn_id),
                    event="failed",
                    reason=payload.reason,
                )
            )
    return cancellations


def normalize_task_plans(
    session_id: SessionId,
    repository: SessionRepository,
) -> list[ReplayTaskPlanSnapshot]:
    task_repository = cast(TaskPlanRepository, repository)
    task_plans: list[ReplayTaskPlanSnapshot] = []
    for task in task_repository.list_tasks(session_id=session_id):
        steps = task_repository.list_task_steps(session_id, task.task_id)
        step_order_by_id = {step.step_id: step.order for step in steps}
        task_plans.append(
            ReplayTaskPlanSnapshot(
                title=task.title,
                goal=task.goal,
                status=enum_value(task.status),
                blocked_reason=enum_optional_value(task.blocked_reason),
                blocked_detail=task.blocked_detail,
                current_step_order=(
                    None
                    if task.current_step_id is None
                    else step_order_by_id.get(task.current_step_id)
                ),
                steps=[
                    ReplayTaskStepSnapshot(
                        title=step.title,
                        order=step.order,
                        status=enum_value(step.status),
                        description=step.description,
                        blocked_reason=enum_optional_value(step.blocked_reason),
                    )
                    for step in steps
                ],
                verifications=[
                    ReplayTaskVerificationSnapshot(
                        check_name=verification.check_name,
                        status=enum_value(verification.status),
                        step_order=(
                            None
                            if verification.step_id is None
                            else step_order_by_id.get(verification.step_id)
                        ),
                        summary=verification.summary,
                    )
                    for verification in task_repository.list_task_verifications(
                        session_id,
                        task.task_id,
                    )
                ],
            )
        )
    return task_plans


def normalize_budget_posture(
    session_id: SessionId,
    repository: SessionRepository,
) -> ReplayBudgetSnapshot | None:
    get_budget_posture = getattr(repository, "get_budget_posture", None)
    if get_budget_posture is None:
        return None
    posture = get_budget_posture(session_id)
    if posture is None:
        return None
    payload = {
        "mode": enum_optional_value(posture.mode),
        "last_decision": posture.last_decision,
        "last_reason": enum_optional_value(posture.last_reason),
        "last_limit_name": posture.last_limit_name,
        "usage": posture.usage.model_dump(mode="json"),
        "remaining": (
            posture.remaining.model_dump(mode="json")
            if posture.remaining is not None
            else None
        ),
    }
    return ReplayBudgetSnapshot(
        **payload,
        fingerprint=fingerprint_replay_payload(payload),
    )


def normalize_long_run_events(
    events: Sequence[EventEnvelope],
) -> list[ReplayLongRunEventSnapshot]:
    normalized: list[ReplayLongRunEventSnapshot] = []
    tool_attempt_ids: dict[str, str] = {}
    tool_call_ids: dict[str, str] = {}
    turn_ids: dict[str, str] = {}
    for event in events:
        payload = event.payload
        if not isinstance(
            payload,
            (
                LongRunPhaseChanged,
                TaskCheckpointCreated,
                ContextCompactionCreated,
                ToolAttemptHeartbeat,
                RecoveryDecisionRecorded,
                ResumeOutcomeRecorded,
            ),
        ):
            continue
        task_id = optional_identifier(event.task_id)
        turn_id = optional_identifier(event.turn_id)
        tool_call_id = optional_identifier(event.tool_call_id)
        tool_attempt_id = optional_identifier(event.tool_attempt_id)
        if isinstance(payload, ToolAttemptHeartbeat):
            turn_id = _stable_replay_identifier(turn_ids, turn_id, prefix="turn")
            tool_call_id = _stable_replay_identifier(
                tool_call_ids,
                tool_call_id,
                prefix="tool_call",
            )
            tool_attempt_id = _stable_replay_identifier(
                tool_attempt_ids,
                tool_attempt_id,
                prefix="tool_attempt",
            )
        raw = {
            "event_type": event.event_type,
            "task_id": task_id,
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "tool_attempt_id": tool_attempt_id,
            "checkpoint_id": optional_identifier(event.checkpoint_id),
            "compaction_id": optional_identifier(event.compaction_id),
            "recovery_decision_id": optional_identifier(event.recovery_decision_id),
            "status": long_run_status(payload),
            "phase": enum_optional_value(getattr(payload, "phase", None)),
        }
        normalized.append(
            ReplayLongRunEventSnapshot(
                **raw,
                fingerprint=fingerprint_replay_payload(raw),
            )
        )
    return normalized


def _stable_replay_identifier(
    identifiers: dict[str, str],
    value: str | None,
    *,
    prefix: str,
) -> str | None:
    if value is None:
        return None
    stable_value = identifiers.get(value)
    if stable_value is None:
        stable_value = f"{prefix}:{len(identifiers)}"
        identifiers[value] = stable_value
    return stable_value


def collect_mismatches(
    baseline: ReplayNormalizedSession,
    replay: ReplayNormalizedSession,
) -> list[str]:
    mismatches: list[str] = []
    baseline_dump = baseline.model_dump(mode="json")
    replay_dump = replay.model_dump(mode="json")
    for field_name in (
        "transcript",
        "lineage",
        "inherited_transcript",
        "post_fork_transcript",
        "tool_calls",
        "approvals",
        "questions",
        "cancellations",
        "task_plans",
        "budget_posture",
        "long_run_events",
        "event_families",
        "final_state",
    ):
        if baseline_dump[field_name] != replay_dump[field_name]:
            mismatches.append(f"{field_name} drift")
    return mismatches


def hydrate_lineage_aware_bundle(bundle: ReplayBundle) -> ReplayBundle:
    baseline_updates: dict[str, object] = {}
    baseline = bundle.baseline

    lineage = baseline.lineage
    if lineage is None:
        lineage = normalize_lineage_from_session_config(bundle.session_config)
        if lineage is not None:
            baseline_updates["lineage"] = lineage

    inherited_transcript = list(baseline.inherited_transcript)
    if not inherited_transcript and bundle.inherited_messages:
        inherited_transcript = [
            normalize_transcript_message(message.role, message.parts)
            for message in bundle.inherited_messages
        ]
        baseline_updates["inherited_transcript"] = inherited_transcript

    if not baseline.post_fork_transcript and baseline.transcript:
        inherited_count = len(inherited_transcript)
        baseline_updates["post_fork_transcript"] = list(
            baseline.transcript[inherited_count:]
        )

    if not baseline_updates:
        return bundle

    return bundle.model_copy(
        update={"baseline": baseline.model_copy(update=baseline_updates)}
    )


def normalize_lineage(session: SessionRecord) -> ReplayLineageSnapshot | None:
    return normalize_lineage_from_session_config(
        SessionConfig(
            model_name=session.model_name,
            cwd=session.cwd,
            approval_mode=session.approval_mode,
            dashboard_url=None,
            parent_session_id=session.parent_session_id,
            forked_from_turn_id=session.forked_from_turn_id,
            forked_from_sequence=session.forked_from_sequence,
            branch_label=session.branch_label,
        )
    )


def normalize_lineage_from_session_config(
    session_config: SessionConfig,
) -> ReplayLineageSnapshot | None:
    if (
        session_config.parent_session_id is None
        or session_config.forked_from_turn_id is None
        or session_config.forked_from_sequence is None
    ):
        return None
    return ReplayLineageSnapshot(
        parent_session_id=str(session_config.parent_session_id),
        forked_from_turn_id=str(session_config.forked_from_turn_id),
        forked_from_sequence=session_config.forked_from_sequence,
        branch_label=session_config.branch_label,
    )


def normalize_transcript_message(
    role: str,
    parts: Sequence[Any],
) -> ReplayTranscriptMessage:
    return ReplayTranscriptMessage(
        role=role,
        parts=[ReplayTranscriptPart(kind=part.kind, text=part.text) for part in parts],
    )


def enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def enum_optional_value(value: Any | None) -> str | None:
    if value is None:
        return None
    return enum_value(value)


def optional_identifier(value: object | None) -> str | None:
    return None if value is None else str(value)


def long_run_status(payload: object) -> str | None:
    for attribute_name in ("state", "status", "freshness", "decision", "outcome"):
        value = getattr(payload, attribute_name, None)
        if value is not None:
            return enum_optional_value(value)
    return None
