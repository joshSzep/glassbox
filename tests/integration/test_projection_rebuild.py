"""Integration tests for projection rebuild from canonical events (GBX-101)."""

from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import open_database


def test_cli_rebuild_restores_one_session_projections_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, rebuilt_session_id = _seed_session_with_projections(
        tmp_path,
        prompt="Inspect session one",
    )
    _, untouched_session_id = _seed_session_with_projections(
        tmp_path,
        prompt="Inspect session two",
        db_path=db_path,
    )
    _ = capsys.readouterr()

    _wipe_session_projections(db_path, rebuilt_session_id)
    _wipe_session_projections(db_path, untouched_session_id)

    exit_code = main(
        [
            "rebuild",
            str(rebuilt_session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    rebuilt_counts = _projection_counts(db_path, rebuilt_session_id)
    untouched_counts = _projection_counts(db_path, untouched_session_id)

    assert exit_code == 0
    assert f"Rebuilt projections for session {rebuilt_session_id}" in captured.out
    assert rebuilt_counts == {
        "session_state": 1,
        "transcript_messages": 2,
        "tool_calls": 1,
        "approvals": 1,
    }
    assert untouched_counts == {
        "session_state": 0,
        "transcript_messages": 0,
        "tool_calls": 0,
        "approvals": 0,
    }


def test_cli_rebuild_all_restores_all_sessions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, first_session_id = _seed_session_with_projections(
        tmp_path,
        prompt="Inspect session one",
    )
    _, second_session_id = _seed_session_with_projections(
        tmp_path,
        prompt="Inspect session two",
        db_path=db_path,
    )
    _ = capsys.readouterr()

    _wipe_all_projections(db_path)

    exit_code = main(
        [
            "rebuild",
            "--all",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    first_counts = _projection_counts(db_path, first_session_id)
    second_counts = _projection_counts(db_path, second_session_id)

    assert exit_code == 0
    assert f"Rebuilt projections for session {first_session_id}" in captured.out
    assert f"Rebuilt projections for session {second_session_id}" in captured.out
    assert "Rebuilt projections for 2 session(s)" in captured.out
    assert first_counts == {
        "session_state": 1,
        "transcript_messages": 2,
        "tool_calls": 1,
        "approvals": 1,
    }
    assert second_counts == {
        "session_state": 1,
        "transcript_messages": 2,
        "tool_calls": 1,
        "approvals": 1,
    }


def test_cli_rebuild_requires_exactly_one_target(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _seed_session_with_projections(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "rebuild",
            str(session_id),
            "--all",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == "specify exactly one of session_id or --all"


def _seed_session_with_projections(
    tmp_path: Path,
    *,
    prompt: str = "Inspect the repository",
    db_path: Path | None = None,
) -> tuple[Path, UUID]:
    resolved_db_path = db_path or (tmp_path / ".glassbox" / "glassbox.sqlite3")
    existing_session_ids = {
        session.session_id for session in _list_sessions(resolved_db_path)
    }
    argv = ["run", prompt, "--cwd", str(tmp_path), "--db-path", str(resolved_db_path)]
    exit_code = main(argv)
    assert exit_code == 0

    connection = open_database(resolved_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        new_sessions = [
            session
            for session in sessions
            if session.session_id not in existing_session_ids
        ]
        assert len(new_sessions) == 1
        session_id = new_sessions[0].session_id
        turn_id = new_turn_id()
        tool_call_id = new_tool_call_id()
        approval_id = new_approval_id()
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                ),
            )
        )
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    success=True,
                    summary="done",
                ),
            )
        )
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    reason="needs confirmation",
                    subject="read_file",
                ),
            )
        )
    finally:
        connection.close()

    return resolved_db_path, session_id


def _list_sessions(db_path: Path) -> list:
    if not db_path.exists():
        return []

    connection = open_database(db_path)
    try:
        return SQLiteSessionRepository(connection).list_sessions()
    finally:
        connection.close()


def _wipe_session_projections(db_path: Path, session_id: UUID) -> None:
    connection = open_database(db_path)
    try:
        with connection:
            connection.execute(
                "delete from session_state where session_id = ?",
                (str(session_id),),
            )
            connection.execute(
                "delete from transcript_messages where session_id = ?",
                (str(session_id),),
            )
            connection.execute(
                "delete from tool_calls where session_id = ?",
                (str(session_id),),
            )
            connection.execute(
                "delete from approvals where session_id = ?",
                (str(session_id),),
            )
    finally:
        connection.close()


def _wipe_all_projections(db_path: Path) -> None:
    connection = open_database(db_path)
    try:
        with connection:
            connection.execute("delete from session_state")
            connection.execute("delete from transcript_messages")
            connection.execute("delete from tool_calls")
            connection.execute("delete from approvals")
    finally:
        connection.close()


def _projection_counts(db_path: Path, session_id: UUID) -> dict[str, int]:
    connection = open_database(db_path)
    try:
        return {
            "session_state": connection.execute(
                "select count(*) from session_state where session_id = ?",
                (str(session_id),),
            ).fetchone()[0],
            "transcript_messages": connection.execute(
                "select count(*) from transcript_messages where session_id = ?",
                (str(session_id),),
            ).fetchone()[0],
            "tool_calls": connection.execute(
                "select count(*) from tool_calls where session_id = ?",
                (str(session_id),),
            ).fetchone()[0],
            "approvals": connection.execute(
                "select count(*) from approvals where session_id = ?",
                (str(session_id),),
            ).fetchone()[0],
        }
    finally:
        connection.close()
