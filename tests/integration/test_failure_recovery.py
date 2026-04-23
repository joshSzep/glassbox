"""Integration tests for failure handling and recovery paths (GBX-131)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core import SessionConfig, SessionStatus
from glassbox.core.events import SessionFailed, ToolExecutionCompleted, TurnFailed
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.store import SQLiteSessionRepository, initialize_database, open_database


def _default_db_path(tmp_path: Path) -> Path:
    return tmp_path / ".glassbox" / "glassbox.sqlite3"


def _open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _only_session_id(db_path: Path) -> UUID:
    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
    finally:
        connection.close()

    assert len(sessions) == 1
    return sessions[0].session_id


def _patch_model_executor(
    monkeypatch: pytest.MonkeyPatch,
    model_fn,
) -> None:
    def build_executor(session) -> PydanticAIModelExecutor:
        return PydanticAIModelExecutor(
            FunctionModel(function=model_fn, model_name=session.model_name)
        )

    monkeypatch.setattr(runtime_bootstrap, "_build_model_executor", build_executor)


def _run_cli(
    tmp_path: Path,
    argv: list[str],
) -> tuple[int, Path]:
    db_path = _default_db_path(tmp_path)
    exit_code = main([*argv, "--cwd", str(tmp_path), "--db-path", str(db_path)])
    return exit_code, db_path


def _raise_model_error(messages: list[Any], _agent_info: Any) -> ModelResponse:
    for message in messages:
        if isinstance(message, ModelRequest):
            break
    raise RuntimeError("model backend unavailable")


def _missing_file_tool_response(
    messages: list[Any],
    _agent_info: Any,
) -> ModelResponse:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if getattr(part, "tool_name", None) == "read_file":
                raise AssertionError("unexpected tool return for failing tool call")

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="read_file",
                args={"path": "missing.txt", "start_line": 1, "end_line": 1},
                tool_call_id="provider-call-missing-file-1",
            )
        ]
    )


def test_cli_run_surfaces_model_failure_and_persists_turn_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_model_executor(monkeypatch, _raise_model_error)

    exit_code, db_path = _run_cli(tmp_path, ["run", "Inspect the repository"])
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 1
    assert "Turn failed: model backend unavailable" in captured.out
    assert captured.err.strip() == "model backend unavailable"
    assert any(isinstance(event.payload, TurnFailed) for event in events)
    assert state is not None
    assert state.status == "running"


def test_cli_run_records_failed_tool_execution_and_turn_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_model_executor(monkeypatch, _missing_file_tool_response)

    exit_code, db_path = _run_cli(tmp_path, ["run", "Read the missing file"])
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        tool_calls = repository.list_tool_calls(session_id)
    finally:
        connection.close()

    assert exit_code == 1
    assert (
        "Tool completed: read_file failed: file does not exist: missing.txt"
        in captured.out
    )
    assert "Turn failed: file does not exist: missing.txt" in captured.out
    assert captured.err.strip() == "file does not exist: missing.txt"
    assert any(
        isinstance(event.payload, ToolExecutionCompleted)
        and event.payload.success is False
        and event.payload.summary == "file does not exist: missing.txt"
        for event in events
    )
    assert tool_calls[0].status == "failed"
    assert tool_calls[0].summary == "file does not exist: missing.txt"


def test_cli_run_surfaces_database_write_failure_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original_append_event = SQLiteSessionRepository.append_event
    append_count = 0

    def flaky_append_event(self, event):
        nonlocal append_count
        append_count += 1
        if append_count == 2:
            raise sqlite3.OperationalError("database is locked")
        return original_append_event(self, event)

    monkeypatch.setattr(
        SQLiteSessionRepository,
        "append_event",
        flaky_append_event,
    )

    exit_code, db_path = _run_cli(tmp_path, ["run", "Inspect the repository"])
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 1
    assert "Started session" in captured.out
    assert captured.err.strip() == "database operation failed: database is locked"
    assert [event.event_type for event in events] == ["SessionStarted"]


def test_invalid_persisted_approval_mode_emits_session_failed(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_db(_default_db_path(tmp_path))
        try:
            runtime_context = runtime_bootstrap._build_runtime_context(
                connection,
                tmp_path,
            )
            session_service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            connection.execute(
                "update sessions set approval_mode = ? where session_id = ?",
                ("invalid-mode", str(state.session_id)),
            )
            connection.commit()

            with pytest.raises(ValueError, match="invalid approval mode persisted"):
                await session_service.submit_user_message(
                    state.session_id,
                    "Inspect the repository",
                )

            events = repository.read_session_events(state.session_id)
            session_state = repository.get_session_state(state.session_id)
        finally:
            connection.close()

        assert any(isinstance(event.payload, TurnFailed) for event in events)
        session_failed_events = [
            event.payload
            for event in events
            if isinstance(event.payload, SessionFailed)
        ]
        assert len(session_failed_events) == 1
        assert session_failed_events[0].error_message == (
            "invalid approval mode persisted for session: invalid-mode"
        )
        assert session_failed_events[0].retryable is False
        assert session_state is not None
        assert session_state.status == SessionStatus.FAILED

    import asyncio

    asyncio.run(scenario())


def test_cli_run_with_partial_provider_config_emits_session_failed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".env").write_text("OPENAI_BASE_URL=https://api.openai.example/v1\n")

    exit_code, db_path = _run_cli(tmp_path, ["run", "Inspect the repository"])
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    session_failed_events = [
        event.payload for event in events if isinstance(event.payload, SessionFailed)
    ]

    assert exit_code == 1
    assert (
        "Session failed: missing OpenAI API key for configured provider runtime"
        in captured.out
    )
    assert (
        captured.err.strip() == "missing OpenAI API key for configured provider runtime"
    )
    assert any(isinstance(event.payload, TurnFailed) for event in events)
    assert len(session_failed_events) == 1
    assert session_failed_events[0].error_message == (
        "missing OpenAI API key for configured provider runtime"
    )
    assert session_failed_events[0].retryable is False
    assert state is not None
    assert state.status == SessionStatus.FAILED


def test_cli_run_with_unsupported_provider_emits_session_failed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, db_path = _run_cli(
        tmp_path,
        ["run", "Inspect the repository", "--model-name", "other:model"],
    )
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    session_failed_events = [
        event.payload for event in events if isinstance(event.payload, SessionFailed)
    ]

    assert exit_code == 1
    assert (
        "Session failed: unsupported model provider configured for session: other"
        in captured.out
    )
    assert (
        captured.err.strip()
        == "unsupported model provider configured for session: other"
    )
    assert len(session_failed_events) == 1
    assert session_failed_events[0].error_message == (
        "unsupported model provider configured for session: other"
    )
    assert state is not None
    assert state.status == SessionStatus.FAILED


def test_cli_run_redacts_provider_secrets_from_surfaced_config_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "super-secret-openai-key"
    (tmp_path / ".env").write_text(
        f"OPENAI_API_KEY={secret}\nOPENAI_BASE_URL=not-a-url\n"
    )

    exit_code, db_path = _run_cli(tmp_path, ["run", "Inspect the repository"])
    captured = capsys.readouterr()
    session_id = _only_session_id(db_path)

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    session_failed_events = [
        event.payload for event in events if isinstance(event.payload, SessionFailed)
    ]

    assert exit_code == 1
    assert "Session failed: invalid OpenAI base URL runtime config" in captured.out
    assert captured.err.strip() == "invalid OpenAI base URL runtime config"
    assert len(session_failed_events) == 1
    assert session_failed_events[0].error_message == (
        "invalid OpenAI base URL runtime config"
    )
    assert secret not in captured.out
    assert secret not in captured.err
    assert all(secret not in event.model_dump_json() for event in events)
    assert state is not None
    assert state.status == SessionStatus.FAILED


def test_cli_rebuild_surfaces_projection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, db_path = _run_cli(tmp_path, ["run", "Inspect the repository"])
    assert exit_code == 0
    _ = capsys.readouterr()
    session_id = _only_session_id(db_path)

    def fail_rebuild(self, session_id: UUID) -> None:  # noqa: ARG001
        raise RuntimeError("projection rebuild failed")

    monkeypatch.setattr(
        SQLiteSessionRepository,
        "rebuild_session_projections",
        fail_rebuild,
    )

    exit_code = main(
        [
            "rebuild",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == "projection rebuild failed"
