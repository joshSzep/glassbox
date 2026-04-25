"""End-to-end scenario coverage for core operator flows (GBX-130)."""

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import SessionResumed
from glassbox.core.events import ToolExecutionCompleted
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database
from glassbox.web import create_app
from glassbox.web.routes.events import _event_stream  # noqa: PLC2701

ModelFn = Callable[[list[Any], Any], ModelResponse]

_PATCH_CALL_ID = "provider-call-e2e-patch-1"
_PATCH_ARGS = {
    "path": "hello.txt",
    "old_text": "",
    "new_text": "Hello from e2e approval flow.\n",
}


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


def _patch_model_executor(monkeypatch: pytest.MonkeyPatch, model_fn: ModelFn) -> None:
    def build_executor(session) -> PydanticAIModelExecutor:
        return PydanticAIModelExecutor(
            FunctionModel(function=model_fn, model_name=session.model_name)
        )

    monkeypatch.setattr(runtime_bootstrap, "_build_model_executor", build_executor)


def _run_cli_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_fn: ModelFn,
    *,
    prompt: str,
    approval_mode: str = "confirm",
) -> tuple[Path, UUID]:
    _patch_model_executor(monkeypatch, model_fn)
    db_path = _default_db_path(tmp_path)
    exit_code = main(
        [
            "session",
            "run",
            prompt,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--approval-mode",
            approval_mode,
        ]
    )

    assert exit_code == 0
    return db_path, _only_session_id(db_path)


def _text_only_response(messages: list[Any], _agent_info: Any) -> ModelResponse:
    prompt = ""
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                prompt = part.content

    return ModelResponse(parts=[TextPart(content=f"I received your request: {prompt}")])


def _readme_tool_then_text_response(
    messages: list[Any],
    _agent_info: Any,
) -> ModelResponse:
    saw_tool_return = False
    tool_content: Any = None

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "read_file":
                saw_tool_return = True
                tool_content = part.content

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="read_file",
                    args={"path": "README.md", "start_line": 1, "end_line": 1},
                    tool_call_id="provider-call-e2e-readme-1",
                )
            ]
        )

    assert isinstance(tool_content, dict)
    return ModelResponse(
        parts=[TextPart(content=f"README says: {tool_content['content']}")]
    )


def _patch_then_text_response(messages: list[Any], _agent_info: Any) -> ModelResponse:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "apply_patch":
                return ModelResponse(parts=[TextPart(content="Patch applied.")])

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="apply_patch",
                args=_PATCH_ARGS,
                tool_call_id=_PATCH_CALL_ID,
            )
        ]
    )


class _MockRequest:
    def __init__(self, *, disconnect_after: int = 0) -> None:
        self._calls = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        result = self._calls >= self._disconnect_after
        self._calls += 1
        return result


async def _collect_frames(generator: AsyncIterator[str]) -> list[str]:
    frames: list[str] = []
    async for frame in generator:
        frames.append(frame)
    return frames


def _parse_sse_frames(text: str) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("data:"):
            current["data"] = line[len("data:") :].strip()
        elif line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("id:"):
            current["id"] = line[len("id:") :].strip()
        elif line == "" and current:
            frames.append(current)
            current = {}
    if current:
        frames.append(current)
    return frames


def test_e2e_run_starts_session_and_persists_assistant_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_cli_session(
        tmp_path,
        monkeypatch,
        _text_only_response,
        prompt="Inspect the repository",
    )
    captured = capsys.readouterr()

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert "Started session" in captured.out
    assert "Assistant: I received your request: Inspect the repository" in captured.out
    assert state is not None
    assert state.status == "running"
    assert [message.role for message in transcript] == ["user", "assistant"]
    assert (
        transcript[-1].parts[0].text
        == "I received your request: Inspect the repository"
    )


def test_e2e_run_completes_tool_assisted_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "README.md").write_text("Glassbox e2e tool turn\n", encoding="utf-8")

    db_path, session_id = _run_cli_session(
        tmp_path,
        monkeypatch,
        _readme_tool_then_text_response,
        prompt="Inspect the repo",
    )
    captured = capsys.readouterr()

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        events = repository.read_session_events(session_id)
        transcript = repository.list_transcript_messages(session_id)
    finally:
        connection.close()

    assert "Tool requested: read_file" in captured.out
    assert "Tool started: read_file" in captured.out
    assert "Tool completed: read_file succeeded: read_file completed" in captured.out
    assert transcript[-1].parts[0].text == "README says: Glassbox e2e tool turn"
    assert any(isinstance(event.payload, ToolExecutionCompleted) for event in events)


def test_e2e_approval_required_turn_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_cli_session(
        tmp_path,
        monkeypatch,
        _patch_then_text_response,
        prompt="Apply the patch",
    )
    run_output = capsys.readouterr()

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        state = repository.get_session_state(session_id)
        approvals = repository.list_approvals(session_id)
    finally:
        connection.close()

    assert "Approval requested: apply_patch" in run_output.out
    assert state is not None
    assert state.status == "awaiting_approval"
    assert len(approvals) == 1
    approval_id = approvals[0].approval_id

    exit_code = main(
        [
            "session",
            "status",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    status_output = capsys.readouterr()

    assert exit_code == 0
    assert "Status: awaiting_approval" in status_output.out
    assert "Pending approvals: 1" in status_output.out

    exit_code = main(
        [
            "session",
            "approve",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    approve_output = capsys.readouterr()

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
        approval_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Approval resolved: approved by user" in approve_output.out
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == _PATCH_ARGS[
        "new_text"
    ]
    assert state is not None
    assert state.status == "running"
    assert transcript[-1].parts[0].text == "Patch applied."
    assert any(
        isinstance(event.payload, ApprovalRequested) for event in approval_events
    )


def test_e2e_resume_reopens_existing_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_cli_session(
        tmp_path,
        monkeypatch,
        _text_only_response,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "resume",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        state = repository.get_session_state(session_id)
        events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Resumed session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert isinstance(events[-1].payload, SessionResumed)


def test_e2e_dashboard_snapshot_and_event_stream_reflect_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path, session_id = _run_cli_session(
        tmp_path,
        monkeypatch,
        _text_only_response,
        prompt="Inspect the repository",
    )

    async def scenario() -> None:
        connection = _open_db(db_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["session_id"] == str(session_id)
            assert body["status"] == "running"
            assert len(body["transcript"]) == 2
            assert body["transcript"][-1]["parts"][0]["text"] == (
                "I received your request: Inspect the repository"
            )

            frames = await _collect_frames(
                _event_stream(
                    _MockRequest(disconnect_after=0),
                    runtime_context,
                    session_id,
                    0,
                )
            )
        finally:
            connection.close()

        parsed = _parse_sse_frames("".join(frames))
        event_types = {frame["event"] for frame in parsed}
        payload_event_types = {
            json.loads(frame["data"])["event_type"] for frame in parsed
        }

        assert "SessionStarted" in event_types
        assert "AssistantMessageCompleted" in event_types
        assert "SessionStarted" in payload_event_types
        assert "TurnCompleted" in payload_event_types

    asyncio.run(scenario())
