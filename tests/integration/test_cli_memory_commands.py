"""CLI coverage for workspace memory inspection commands."""

import json
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import new_session_id
from glassbox.core import new_workspace_memory_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_memory_list_show_confirm_invalidate_and_prune_commands(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    memory_id = new_workspace_memory_id()
    _seed_memory(db_path, tmp_path, session_id, memory_id)

    list_exit = main(
        [
            "memory",
            "list",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    list_output = capsys.readouterr().out

    query_exit = main(
        [
            "memory",
            "list",
            "--query",
            "pytest",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    query_payload = json.loads(capsys.readouterr().out)

    show_exit = main(
        [
            "memory",
            "show",
            str(memory_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    show_payload = json.loads(capsys.readouterr().out)

    confirm_exit = main(
        [
            "memory",
            "confirm",
            str(memory_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    confirm_payload = json.loads(capsys.readouterr().out)

    invalidate_exit = main(
        [
            "memory",
            "invalidate",
            str(memory_id),
            "--reason",
            "command changed",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    invalidate_payload = json.loads(capsys.readouterr().out)

    dry_run_exit = main(
        [
            "memory",
            "prune",
            str(memory_id),
            "--reason",
            "superseded",
            "--dry-run",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    dry_run_payload = json.loads(capsys.readouterr().out)

    prune_exit = main(
        [
            "memory",
            "prune",
            str(memory_id),
            "--reason",
            "superseded",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    prune_payload = json.loads(capsys.readouterr().out)

    assert list_exit == 0
    assert "Workspace memory: 1" in list_output
    assert "backend pytest command" in list_output
    assert query_exit == 0
    assert query_payload[0]["memory_id"] == str(memory_id)
    assert show_exit == 0
    assert show_payload["memory_id"] == str(memory_id)
    assert show_payload["provenance"]["source_sequence"] == 1
    assert confirm_exit == 0
    assert confirm_payload["confirmed_by"] == "operator"
    assert invalidate_exit == 0
    assert invalidate_payload["state"] == "invalidated"
    assert invalidate_payload["invalidation_reason"] == "command changed"
    assert dry_run_exit == 0
    assert dry_run_payload["state"] == "invalidated"
    assert prune_exit == 0
    assert prune_payload["state"] == "pruned"
    assert prune_payload["prune_reason"] == "superseded"


def test_memory_show_reports_unknown_entry(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    memory_id = new_workspace_memory_id()

    exit_code = main(
        [
            "memory",
            "show",
            str(memory_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"unknown workspace memory: {memory_id}" in captured.err


def _seed_memory(
    db_path: Path,
    tmp_path: Path,
    session_id,
    memory_id,
) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryCreated(
                        memory_id=memory_id,
                        kind=WorkspaceMemoryKind.COMMAND,
                        content="Use uv run pytest for backend tests.",
                        summary="backend pytest command",
                        provenance=WorkspaceMemoryProvenance(
                            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                            session_id=session_id,
                            source_sequence=1,
                        ),
                    ),
                ),
            ]
        )
    finally:
        connection.close()
