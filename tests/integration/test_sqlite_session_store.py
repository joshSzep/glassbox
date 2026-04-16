"""Integration tests for the SQLite session metadata store."""

from datetime import UTC, datetime
from pathlib import Path

from glassbox.core import (
    EventEnvelope,
    SessionCompleted,
    SessionConfig,
    SessionRecord,
    SessionStarted,
    SessionStatus,
    UserMessageReceived,
    new_message_id,
    new_session_id,
)
from glassbox.store import (
    append_events,
    create_session,
    get_session,
    initialize_database,
    list_sessions,
    open_database,
    update_session,
)


def test_create_session_and_get_session_round_trip(tmp_path: Path) -> None:
    session_id = new_session_id()
    created_at = datetime(2026, 4, 16, 12, 0, tzinfo=UTC)
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    try:
        created_session = create_session(
            connection,
            session_id,
            SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=Path("/tmp/glassbox"),
                approval_mode="confirm",
            ),
            status=SessionStatus.IDLE,
            created_at=created_at,
            updated_at=created_at,
        )
        fetched_session = get_session(connection, session_id)
    finally:
        connection.close()

    assert isinstance(created_session, SessionRecord)
    assert fetched_session == created_session


def test_update_session_persists_coarse_metadata(tmp_path: Path) -> None:
    session_id = new_session_id()
    created_at = datetime(2026, 4, 16, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 4, 16, 12, 5, tzinfo=UTC)
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    try:
        create_session(
            connection,
            session_id,
            SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=Path("/tmp/glassbox"),
                approval_mode="confirm",
            ),
            created_at=created_at,
            updated_at=created_at,
        )
        updated_session = update_session(
            connection,
            session_id,
            status=SessionStatus.RUNNING,
            updated_at=updated_at,
            last_sequence=4,
        )
    finally:
        connection.close()

    assert updated_session.status == SessionStatus.RUNNING
    assert updated_session.updated_at == updated_at
    assert updated_session.last_sequence == 4


def test_list_sessions_supports_status_filter_and_recency_order(
    tmp_path: Path,
) -> None:
    older_session_id = new_session_id()
    newer_session_id = new_session_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    try:
        create_session(
            connection,
            older_session_id,
            SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=Path("/tmp/older"),
                approval_mode="confirm",
            ),
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 1, tzinfo=UTC),
        )
        create_session(
            connection,
            newer_session_id,
            SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=Path("/tmp/newer"),
                approval_mode="review",
            ),
            status=SessionStatus.COMPLETED,
            created_at=datetime(2026, 4, 16, 12, 2, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 3, tzinfo=UTC),
        )
        running_sessions = list_sessions(connection, status=SessionStatus.RUNNING)
        all_sessions = list_sessions(connection)
    finally:
        connection.close()

    assert [session.session_id for session in running_sessions] == [older_session_id]
    assert [session.session_id for session in all_sessions] == [
        newer_session_id,
        older_session_id,
    ]


def test_append_events_keeps_session_sequence_and_status_in_sync(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=new_message_id(),
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionCompleted(reason="finished"),
                ),
            ],
        )
        session = get_session(connection, session_id)
    finally:
        connection.close()

    assert session is not None
    assert session.last_sequence == 3
    assert session.status == SessionStatus.COMPLETED
