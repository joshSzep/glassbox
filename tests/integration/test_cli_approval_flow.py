"""End-to-end CLI tests for the full approval pause/resume workflow (GBX-071).

These tests use a two-phase approach:
  1. Phase 1 — service layer: run a real turn with a FunctionModel whose first
     response is a risky tool call, causing the turn to pause at
     SessionStatus.AWAITING_APPROVAL.
  2. Phase 2 — CLI layer: call `main(["approve"/"deny", ...])` against the same
     database to complete the workflow and verify rendered output.
"""

import asyncio
import sqlite3
from pathlib import Path
from uuid import UUID

import pytest
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionConfig
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import TurnCompleted
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_patch_tool_registry

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_PATCH_CALL_ID = "provider-call-cli-patch-1"
_PATCH_ARGS = {
    "path": "hello.txt",
    "old_text": "",
    "new_text": "Hello from CLI approval!\n",
}


# ---------------------------------------------------------------------------
# FunctionModel callbacks for phase 1
# ---------------------------------------------------------------------------


def _patch_tool_call_only(messages, _agent_info) -> ModelResponse:
    """Always returns a risky apply_patch call (never sees a tool return)."""
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="apply_patch",
                args=_PATCH_ARGS,
                tool_call_id=_PATCH_CALL_ID,
            )
        ]
    )


def _patch_then_ack(messages, _agent_info) -> ModelResponse:
    """First call returns a patch, second acknowledges the tool result."""
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "apply_patch":
                    return ModelResponse(parts=[TextPart(content="Patch done.")])
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="apply_patch",
                args=_PATCH_ARGS,
                tool_call_id=_PATCH_CALL_ID,
            )
        ]
    )


# ---------------------------------------------------------------------------
# Phase 1 helpers
# ---------------------------------------------------------------------------


def _default_db_path(tmp_path: Path) -> Path:
    """Replicate the CLI's default database path convention."""
    return tmp_path / ".glassbox" / "glassbox.sqlite3"


def _open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


async def _run_until_awaiting_approval(
    db_path: Path,
    tmp_path: Path,
    model_fn,
) -> tuple[UUID, UUID]:
    """Start a session with *model_fn*, submit a message, and wait until the
    session suspends at AWAITING_APPROVAL.  Returns (session_id, approval_id)."""

    connection = _open_db(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        bus: EventBus[EventEnvelope] = EventBus()
        turn_engine = TurnEngine(
            repository,
            bus,
            TurnContextBuilder(repository),
            lambda _session: PydanticAIModelAdapter(
                ModelProviderConfig(provider="openai", model_name="gpt-5.4")
            ),
            lambda _session: PydanticAIModelExecutor(
                FunctionModel(function=model_fn, model_name="openai:gpt-5.4")
            ),
            lambda session: ToolRuntime(
                build_patch_tool_registry(session.cwd),
                ToolPolicyEngine(),
                ToolPolicyContext(
                    workspace_root=session.cwd,
                    approval_mode=ApprovalMode.CONFIRM,
                ),
            ),
        )
        supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
        config = SessionConfig(
            model_name="openai:gpt-5.4",
            cwd=tmp_path,
            approval_mode="confirm",
        )

        async with bus.subscribe() as subscription:
            state = await supervisor.start_session(config)
            await subscription.get()  # SessionStarted

            await supervisor.submit_user_message(state.session_id, "Apply the patch.")

            # Drain events until TurnCompleted(outcome="awaiting_approval")
            while True:
                event = await subscription.get()
                if (
                    isinstance(event.payload, TurnCompleted)
                    and event.payload.outcome == "awaiting_approval"
                ):
                    break

        # Retrieve the approval_id from persisted events
        all_events = repository.read_session_events(state.session_id)
        approval_payload = next(
            (
                ev.payload
                for ev in all_events
                if isinstance(ev.payload, ApprovalRequested)
            ),
            None,
        )
        assert approval_payload is not None, "Expected an ApprovalRequested event"

        return state.session_id, approval_payload.approval_id
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cli_approve_command_resumes_suspended_turn_and_executes_tool(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI `approve` against a real suspended session runs the tool and completes."""

    db_path = _default_db_path(tmp_path)

    session_id, approval_id = asyncio.run(
        _run_until_awaiting_approval(db_path, tmp_path, _patch_tool_call_only)
    )
    _ = capsys.readouterr()  # discard phase-1 output

    exit_code = main(
        [
            "approve",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    # CLI must succeed
    assert exit_code == 0

    # Approval resolution must be rendered
    assert "Approval resolved: approved by user" in captured.out

    # The patch file must have been written by the tool
    assert (tmp_path / "hello.txt").exists()
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == _PATCH_ARGS[
        "new_text"
    ]

    # SQLite must contain a TurnCompleted(outcome="completed") from the resumed turn
    connection = _open_db(db_path)
    try:
        repo = SQLiteSessionRepository(connection)
        all_events = repo.read_session_events(session_id)
    finally:
        connection.close()

    completed_outcomes = [
        ev.payload.outcome for ev in all_events if isinstance(ev.payload, TurnCompleted)
    ]
    assert "completed" in completed_outcomes


def test_cli_deny_command_resumes_suspended_turn_without_executing_tool(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI `deny` against a suspended session resumes the turn; tool does not run."""

    db_path = _default_db_path(tmp_path)

    session_id, approval_id = asyncio.run(
        _run_until_awaiting_approval(db_path, tmp_path, _patch_tool_call_only)
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "deny",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Approval resolved: denied by user" in captured.out

    # File must NOT have been written
    assert not (tmp_path / "hello.txt").exists()

    connection = _open_db(db_path)
    try:
        repo = SQLiteSessionRepository(connection)
        all_events = repo.read_session_events(session_id)
    finally:
        connection.close()

    completed_outcomes = [
        ev.payload.outcome for ev in all_events if isinstance(ev.payload, TurnCompleted)
    ]
    assert "completed" in completed_outcomes


def test_cli_approve_renders_tool_execution_events(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Rendered output from CLI `approve` includes tool execution feedback."""

    db_path = _default_db_path(tmp_path)

    session_id, approval_id = asyncio.run(
        _run_until_awaiting_approval(db_path, tmp_path, _patch_tool_call_only)
    )
    _ = capsys.readouterr()

    main(
        [
            "approve",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    # Tool events must appear in terminal output
    assert "Tool started: apply_patch" in captured.out
    assert "Tool completed: apply_patch succeeded" in captured.out
