"""Normalization and mismatch comparison helpers for deterministic replay."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_models import ReplayApprovalSnapshot
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayFinalStateSnapshot
from glassbox.runtime.replay_models import ReplayLineageSnapshot
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.replay_models import ReplayQuestionSnapshot
from glassbox.runtime.replay_models import ReplayToolCallSnapshot
from glassbox.runtime.replay_models import ReplayTranscriptMessage
from glassbox.runtime.replay_models import ReplayTranscriptPart
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
