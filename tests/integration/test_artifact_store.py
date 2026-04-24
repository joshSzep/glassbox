"""Integration tests for file-backed artifact storage."""

from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import ToolArtifactRecorded
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.artifacts import read_binary_artifact
from glassbox.store.artifacts import read_text_artifact
from glassbox.store.artifacts import record_text_artifact
from glassbox.store.artifacts import write_binary_artifact
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.store.sqlite import read_events_by_correlation_id


def test_record_text_artifact_writes_session_scoped_file_and_links_event(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    try:
        # Seed the session row required by the event store.
        from glassbox.store.sqlite import append_event

        append_event(
            connection,
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
        )

        stored_artifact, artifact_event = record_text_artifact(
            connection,
            tmp_path,
            session_id,
            turn_id,
            tool_call_id,
            "tool_log",
            "command output\n",
            suffix=".log",
        )
        linked_events = read_events_by_correlation_id(
            connection,
            session_id,
            tool_call_id=tool_call_id,
        )
        restored_text = read_text_artifact(tmp_path, stored_artifact.relative_path)
    finally:
        connection.close()

    assert isinstance(artifact_event.payload, ToolArtifactRecorded)
    assert isinstance(linked_events[-1].payload, ToolArtifactRecorded)

    assert stored_artifact.absolute_path.exists()
    assert stored_artifact.relative_path.parts[:3] == (
        ".glassbox",
        "sessions",
        str(session_id),
    )
    assert restored_text == "command output\n"
    assert artifact_event.payload.path == stored_artifact.relative_path.as_posix()
    assert linked_events[-1].payload.event_type == "ToolArtifactRecorded"
    assert linked_events[-1].payload.path == stored_artifact.relative_path.as_posix()


def test_write_and_read_binary_artifact_round_trip(tmp_path: Path) -> None:
    session_id = new_session_id()

    stored_artifact = write_binary_artifact(
        tmp_path,
        session_id,
        b"\x00\x01glassbox",
        suffix="bin",
    )
    restored_bytes = read_binary_artifact(tmp_path, stored_artifact.relative_path)

    assert stored_artifact.absolute_path.exists()
    assert restored_bytes == b"\x00\x01glassbox"
