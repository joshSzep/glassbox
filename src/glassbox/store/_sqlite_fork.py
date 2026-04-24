"""Fork-point resolution and transcript import helpers for SQLite sessions."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from glassbox.core.events import (
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    EventEnvelope,
    TranscriptMessageImported,
    TurnCompleted,
    UserMessageReceived,
)
from glassbox.core.ids import MessageId, SessionId, TurnId
from glassbox.core.models import (
    InheritedTranscriptMessage,
    MessagePart,
    ResolvedForkPoint,
)
from glassbox.core.types import SessionStatus
from glassbox.store._sqlite_events import read_session_events
from glassbox.store._sqlite_sessions import get_session, get_session_state
from glassbox.store._sqlite_utils import _derived_imported_message_id


def resolve_fork_point(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    turn_id: TurnId | None = None,
) -> ResolvedForkPoint:
    """Resolve a stable historical fork boundary from persisted session history."""

    session = get_session(connection, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")

    session_state = get_session_state(connection, session_id)
    if session_state is None:
        raise ValueError(f"unknown session_id: {session_id}")

    if (
        session_state.status == SessionStatus.AWAITING_APPROVAL
        or session_state.pending_approval_id is not None
    ):
        raise ValueError(f"session {session_id} is awaiting approval")
    if (
        session_state.status == SessionStatus.AWAITING_USER_INPUT
        or session_state.pending_question_id is not None
    ):
        raise ValueError(f"session {session_id} is awaiting user input")
    if session_state.current_turn_id is not None:
        raise ValueError(
            f"session {session_id} has active turn {session_state.current_turn_id}"
        )

    session_events = read_session_events(connection, session_id)
    completed_turns = [
        event
        for event in session_events
        if isinstance(event.payload, TurnCompleted)
        and event.payload.outcome == "completed"
    ]

    resolved_event: EventEnvelope | None
    if turn_id is None:
        if not completed_turns:
            raise ValueError(f"session {session_id} has no completed fork point")
        resolved_event = completed_turns[-1]
    else:
        resolved_event = next(
            (event for event in completed_turns if event.turn_id == turn_id),
            None,
        )
        if resolved_event is None:
            turn_known = any(event.turn_id == turn_id for event in session_events)
            if not turn_known:
                raise ValueError(f"unknown turn_id: {turn_id}")
            raise ValueError(f"turn {turn_id} is not a completed fork point")

    resolved_turn_id = resolved_event.turn_id
    if resolved_turn_id is None:
        raise RuntimeError("resolved fork point is missing a turn_id")

    return ResolvedForkPoint(
        parent_session_id=session.session_id,
        turn_id=resolved_turn_id,
        sequence=resolved_event.sequence,
        inherited_messages=_project_inherited_transcript_messages(
            session_events,
            up_to_sequence=resolved_event.sequence,
        ),
    )


def build_imported_transcript_events(
    session_id: SessionId,
    fork_point: ResolvedForkPoint,
) -> list[EventEnvelope]:
    """Create canonical child-session events for inherited transcript history."""

    return [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TranscriptMessageImported(
                message_id=_derived_imported_message_id(
                    session_id,
                    message.source_message_id,
                ),
                source_session_id=fork_point.parent_session_id,
                source_message_id=message.source_message_id,
                source_turn_id=message.source_turn_id,
                role=message.role,
                parts=message.parts,
                source_created_at=message.created_at,
            ),
        )
        for message in fork_point.inherited_messages
    ]


def _project_inherited_transcript_messages(
    events: Sequence[EventEnvelope],
    *,
    up_to_sequence: int,
) -> list[InheritedTranscriptMessage]:
    projected_messages: dict[MessageId, InheritedTranscriptMessage] = {}

    for event in events:
        if event.sequence > up_to_sequence:
            break

        payload = event.payload
        if isinstance(payload, UserMessageReceived):
            projected_messages[payload.message_id] = InheritedTranscriptMessage(
                source_message_id=payload.message_id,
                source_turn_id=event.turn_id,
                role="user",
                parts=[MessagePart(kind="text", text=payload.text)],
                created_at=event.created_at,
            )
            continue

        if isinstance(payload, AssistantMessageStarted):
            projected_messages[payload.message_id] = InheritedTranscriptMessage(
                source_message_id=payload.message_id,
                source_turn_id=event.turn_id,
                role="assistant",
                parts=[MessagePart(kind="text", text="")],
                created_at=event.created_at,
            )
            continue

        if isinstance(payload, AssistantMessageDelta):
            current = projected_messages.get(payload.message_id)
            if current is None:
                current = InheritedTranscriptMessage(
                    source_message_id=payload.message_id,
                    source_turn_id=event.turn_id,
                    role="assistant",
                    parts=[MessagePart(kind="text", text="")],
                    created_at=event.created_at,
                )

            current_text = "".join(part.text for part in current.parts)
            projected_messages[payload.message_id] = InheritedTranscriptMessage(
                source_message_id=payload.message_id,
                source_turn_id=current.source_turn_id or event.turn_id,
                role="assistant",
                parts=[MessagePart(kind="text", text=current_text + payload.delta)],
                created_at=current.created_at,
            )
            continue

        if isinstance(payload, AssistantMessageCompleted):
            current = projected_messages.get(payload.message_id)
            projected_messages[payload.message_id] = InheritedTranscriptMessage(
                source_message_id=payload.message_id,
                source_turn_id=(
                    current.source_turn_id if current is not None else event.turn_id
                ),
                role="assistant",
                parts=payload.parts,
                created_at=(
                    current.created_at if current is not None else event.created_at
                ),
            )

    return sorted(
        projected_messages.values(),
        key=lambda message: (message.created_at, str(message.source_message_id)),
    )


__all__ = ["build_imported_transcript_events", "resolve_fork_point"]
