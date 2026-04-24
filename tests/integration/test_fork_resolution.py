"""Integration tests for historical fork-point resolution and imported history."""

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from glassbox.core import (
    ApprovalRequested,
    AssistantMessageCompleted,
    EventEnvelope,
    MessagePart,
    SessionStarted,
    TranscriptMessageImported,
    TurnCompleted,
    TurnFailed,
    TurnStarted,
    UserMessageReceived,
    UserQuestionAsked,
    new_approval_id,
    new_message_id,
    new_question_id,
    new_session_id,
    new_tool_call_id,
    new_turn_id,
)
from glassbox.store import (
    append_events,
    build_imported_transcript_events,
    get_session,
    initialize_database,
    list_transcript_messages,
    open_database,
    read_session_events,
    resolve_fork_point,
)


def _timestamp(minute: int) -> datetime:
    return datetime(2026, 4, 23, 12, minute, tzinfo=UTC)


def _open_initialized_database(tmp_path: Path):
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _append_payloads(connection, session_id, payloads) -> None:
    append_events(
        connection,
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                created_at=_timestamp(index),
                payload=payload,
            )
            for index, payload in enumerate(payloads)
        ],
    )


def _seed_completed_parent(connection):
    session_id = new_session_id()
    first_user_id = new_message_id()
    first_turn_id = new_turn_id()
    first_assistant_id = new_message_id()
    second_user_id = new_message_id()
    second_turn_id = new_turn_id()
    second_assistant_id = new_message_id()
    _append_payloads(
        connection,
        session_id,
        [
            SessionStarted(
                cwd="/tmp/glassbox",
                model_name="openai:gpt-5.4",
                approval_mode="confirm",
            ),
            UserMessageReceived(
                message_id=first_user_id,
                text="first question",
            ),
            TurnStarted(
                turn_id=first_turn_id,
                trigger_message_id=first_user_id,
            ),
            AssistantMessageCompleted(
                message_id=first_assistant_id,
                parts=[MessagePart(kind="text", text="first answer")],
            ),
            TurnCompleted(turn_id=first_turn_id, outcome="completed"),
            UserMessageReceived(
                message_id=second_user_id,
                text="second question",
            ),
            TurnStarted(
                turn_id=second_turn_id,
                trigger_message_id=second_user_id,
            ),
            AssistantMessageCompleted(
                message_id=second_assistant_id,
                parts=[MessagePart(kind="text", text="second answer")],
            ),
            TurnCompleted(turn_id=second_turn_id, outcome="completed"),
        ],
    )
    return {
        "session_id": session_id,
        "first_turn_id": first_turn_id,
        "second_turn_id": second_turn_id,
        "source_message_ids": [
            first_user_id,
            first_assistant_id,
            second_user_id,
            second_assistant_id,
        ],
    }


@pytest.mark.parametrize(
    ("payload_factory", "message_pattern"),
    [
        (
            lambda turn_id: [
                UserMessageReceived(message_id=new_message_id(), text="pending"),
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=new_message_id(),
                ),
            ],
            "has active turn",
        ),
        (
            lambda turn_id: [
                UserMessageReceived(
                    message_id=new_message_id(),
                    text="needs approval",
                ),
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=new_message_id(),
                ),
                ApprovalRequested(
                    approval_id=new_approval_id(),
                    turn_id=turn_id,
                    reason="needs confirmation",
                    subject="apply_patch",
                ),
            ],
            "awaiting approval",
        ),
        (
            lambda turn_id: [
                UserMessageReceived(
                    message_id=new_message_id(),
                    text="needs answer",
                ),
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=new_message_id(),
                ),
                UserQuestionAsked(
                    question_id=new_question_id(),
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    provider_tool_call_id="provider-call-1",
                    question="Continue?",
                ),
            ],
            "awaiting user input",
        ),
    ],
)
def test_resolve_fork_point_rejects_active_and_suspended_sessions(
    tmp_path: Path,
    payload_factory,
    message_pattern: str,
) -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    connection = _open_initialized_database(tmp_path)
    try:
        _append_payloads(
            connection,
            session_id,
            [
                SessionStarted(
                    cwd="/tmp/glassbox",
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
                *payload_factory(turn_id),
            ],
        )

        with pytest.raises(ValueError, match=message_pattern):
            resolve_fork_point(connection, session_id)
    finally:
        connection.close()


def test_resolve_fork_point_returns_latest_or_selected_completed_turn(
    tmp_path: Path,
) -> None:
    connection = _open_initialized_database(tmp_path)
    try:
        parent = _seed_completed_parent(connection)

        latest_fork_point = resolve_fork_point(connection, parent["session_id"])
        first_turn_fork_point = resolve_fork_point(
            connection,
            parent["session_id"],
            turn_id=parent["first_turn_id"],
        )
    finally:
        connection.close()

    assert latest_fork_point.turn_id == parent["second_turn_id"]
    assert latest_fork_point.sequence == 9
    assert [
        message.parts[0].text for message in latest_fork_point.inherited_messages
    ] == [
        "first question",
        "first answer",
        "second question",
        "second answer",
    ]
    assert first_turn_fork_point.turn_id == parent["first_turn_id"]
    assert first_turn_fork_point.sequence == 5
    assert [
        message.parts[0].text for message in first_turn_fork_point.inherited_messages
    ] == ["first question", "first answer"]


def test_resolve_fork_point_rejects_unknown_or_non_completed_turns(
    tmp_path: Path,
) -> None:
    connection = _open_initialized_database(tmp_path)
    try:
        parent = _seed_completed_parent(connection)
        failed_turn_id = new_turn_id()
        failed_message_id = new_message_id()
        _append_payloads(
            connection,
            parent["session_id"],
            [
                UserMessageReceived(
                    message_id=failed_message_id,
                    text="failed branch",
                ),
                TurnStarted(
                    turn_id=failed_turn_id,
                    trigger_message_id=failed_message_id,
                ),
                TurnFailed(
                    turn_id=failed_turn_id,
                    error_message="tool crashed",
                ),
            ],
        )

        with pytest.raises(ValueError, match="unknown turn_id"):
            resolve_fork_point(connection, parent["session_id"], turn_id=new_turn_id())

        with pytest.raises(ValueError, match="is not a completed fork point"):
            resolve_fork_point(connection, parent["session_id"], turn_id=failed_turn_id)
    finally:
        connection.close()


def test_imported_history_events_materialize_child_transcript_without_mutating_parent(
    tmp_path: Path,
) -> None:
    child_session_id = new_session_id()
    connection = _open_initialized_database(tmp_path)
    try:
        parent = _seed_completed_parent(connection)
        fork_point = resolve_fork_point(
            connection,
            parent["session_id"],
            turn_id=parent["first_turn_id"],
        )
        imported_events = build_imported_transcript_events(child_session_id, fork_point)

        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=child_session_id,
                    sequence=0,
                    created_at=_timestamp(20),
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                        parent_session_id=parent["session_id"],
                        forked_from_turn_id=fork_point.turn_id,
                        forked_from_sequence=fork_point.sequence,
                        branch_label="forked-first-turn",
                    ),
                ),
                *imported_events,
            ],
        )

        parent_transcript = list_transcript_messages(connection, parent["session_id"])
        child_transcript = list_transcript_messages(connection, child_session_id)
        child_session = get_session(connection, child_session_id)
        child_events = read_session_events(connection, child_session_id)
        rebuilt_events = build_imported_transcript_events(child_session_id, fork_point)
    finally:
        connection.close()

    child_imported_payloads = cast(
        list[TranscriptMessageImported],
        [event.payload for event in child_events[1:]],
    )
    imported_payloads = cast(
        list[TranscriptMessageImported],
        [event.payload for event in imported_events],
    )
    rebuilt_payloads = cast(
        list[TranscriptMessageImported],
        [event.payload for event in rebuilt_events],
    )

    assert [message.parts[0].text for message in parent_transcript] == [
        "first question",
        "first answer",
        "second question",
        "second answer",
    ]
    assert [message.parts[0].text for message in child_transcript] == [
        "first question",
        "first answer",
    ]
    assert child_session is not None
    assert child_session.parent_session_id == parent["session_id"]
    assert child_session.forked_from_turn_id == fork_point.turn_id
    assert child_session.forked_from_sequence == fork_point.sequence
    assert [event.event_type for event in child_events] == [
        "SessionStarted",
        "TranscriptMessageImported",
        "TranscriptMessageImported",
    ]
    assert [payload.source_message_id for payload in child_imported_payloads] == parent[
        "source_message_ids"
    ][:2]
    assert [payload.message_id for payload in imported_payloads] == [
        payload.message_id for payload in rebuilt_payloads
    ]
    assert [payload.message_id for payload in imported_payloads] != parent[
        "source_message_ids"
    ][:2]
