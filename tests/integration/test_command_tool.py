"""Integration tests for the command runner tool."""

import asyncio
from pathlib import Path

import pytest

from glassbox.core import new_turn_id
from glassbox.runtime.cancellation import TurnCancellationController
from glassbox.tools import DEFAULT_TOOL_POLICY_PATH
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import build_command_tool_registry
from glassbox.tools import load_tool_policy_manifest
from glassbox.tools.command import RunCommandArgs
from glassbox.tools.command import RunCommandTool

# ---------------------------------------------------------------------------
# Direct tool execution
# ---------------------------------------------------------------------------


def test_run_command_captures_stdout(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="echo hello"))
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.timed_out is False
        assert result.truncated is False
        assert result.failure_category is None
        assert result.execution_envelope.requested_cwd == "."
        assert result.execution_envelope.resolved_cwd == "."
        assert result.execution_envelope.directory_policy == "workspace_root"

    asyncio.run(scenario())


def test_run_command_streams_output_chunks(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)
    collected: list[tuple[str, str]] = []

    async def scenario() -> None:
        result = await tool.execute_streaming(
            RunCommandArgs(command="printf 'line1\\nline2\\n'"),
            on_chunk=lambda stream, chunk: collected.append((stream, chunk)),
        )
        assert result.exit_code == 0

    asyncio.run(scenario())
    assert any("line1" in chunk for _stream, chunk in collected)
    assert any("line2" in chunk for _stream, chunk in collected)
    assert all(stream == "stdout" for stream, _chunk in collected)


def test_run_command_captures_non_zero_exit_code(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="exit 42"))
        assert result.exit_code == 42
        assert result.timed_out is False
        assert result.failure_category == "execution_error"

    asyncio.run(scenario())


def test_run_command_captures_stderr(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="echo oops >&2"))
        assert result.exit_code == 0
        assert "oops" in result.stderr

    asyncio.run(scenario())


def test_run_command_times_out(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="sleep 60", timeout=1))
        assert result.timed_out is True
        assert result.exit_code != 0
        assert result.failure_category == "timed_out"
        assert result.execution_envelope.timeout_seconds == 1

    asyncio.run(scenario())


def test_run_command_cancellation_preserves_streamed_output(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)
    cancellation = TurnCancellationController(new_turn_id())
    collected: list[tuple[str, str]] = []

    def on_chunk(stream: str, chunk: str) -> None:
        collected.append((stream, chunk))
        if "ready" in chunk:
            cancellation.request("operator requested cancellation")

    async def scenario() -> None:
        result = await tool.execute_streaming(
            RunCommandArgs(
                command=(
                    'python -u -c "import threading; '
                    "print('ready', flush=True); threading.Event().wait(60)\""
                ),
                timeout=30,
            ),
            on_chunk=on_chunk,
            cancellation_controller=cancellation,
        )
        assert result.cancelled is True
        assert result.timed_out is False
        assert result.failure_category == "cancelled"
        assert "ready" in result.stdout

    asyncio.run(scenario())
    assert collected == [("stdout", "ready\n")]


def test_run_command_classifies_signal_interruption(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            RunCommandArgs(
                command=(
                    "python -c 'import os, signal; "
                    "os.kill(os.getpid(), signal.SIGTERM)'"
                )
            )
        )
        assert result.failure_category == "interrupted"
        assert result.termination_signal == 15

    asyncio.run(scenario())


def test_run_command_records_subdirectory_execution_envelope(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="pwd", cwd="nested"))
        assert result.execution_envelope.requested_cwd == "nested"
        assert result.execution_envelope.resolved_cwd == "nested"
        assert result.execution_envelope.directory_policy == "workspace_subdirectory"

    asyncio.run(scenario())


def test_run_command_uses_workspace_as_default_cwd(tmp_path: Path) -> None:
    (tmp_path / "marker.txt").write_text("found\n", encoding="utf-8")
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunCommandArgs(command="ls"))
        assert "marker.txt" in result.stdout

    asyncio.run(scenario())


def test_run_command_rejects_out_of_scope_cwd(tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await tool.execute(RunCommandArgs(command="echo hi", cwd="../"))

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Registry contents
# ---------------------------------------------------------------------------


def test_build_command_tool_registry_includes_all_tools(tmp_path: Path) -> None:
    registry = build_command_tool_registry(tmp_path)
    tool_names = {tool.spec.name for tool in registry.list_tools()}
    assert tool_names == {"list_dir", "read_file", "search_files", "run_command"}


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------


def test_command_tool_requires_approval_in_confirm_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path,
        approval_mode=ApprovalMode.CONFIRM,
    )
    registry = build_command_tool_registry(tmp_path)
    tool = registry.require("run_command")
    args = RunCommandArgs(command="echo hello")
    decision = engine.evaluate(tool.spec, arguments=args, context=context)

    assert decision.requires_approval is True
    assert decision.allowed is True


def test_command_tool_blocked_in_never_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path,
        approval_mode=ApprovalMode.NEVER,
    )
    registry = build_command_tool_registry(tmp_path)
    tool = registry.require("run_command")
    args = RunCommandArgs(command="echo hello")
    decision = engine.evaluate(tool.spec, arguments=args, context=context)

    assert decision.allowed is False
    assert decision.requires_approval is False


def test_command_tool_blocks_destructive_pattern(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path,
        approval_mode=ApprovalMode.NEVER,
    )
    registry = build_command_tool_registry(tmp_path)
    tool = registry.require("run_command")
    args = RunCommandArgs(command="rm -rf /")
    decision = engine.evaluate(tool.spec, arguments=args, context=context)

    assert decision.allowed is False
    assert "destructive" in decision.reason


def test_command_tool_loads_workspace_policy_manifest(tmp_path: Path) -> None:
    (tmp_path / DEFAULT_TOOL_POLICY_PATH).write_text(
        """
                {
                    "manifest_version": 1,
                    "rules": [
                        {
                            "rule_id": "allow-git-status",
                            "tool_name": "run_command",
                            "action": "allow",
                            "command_prefixes": ["git status"]
                        }
                    ]
                }
                """.strip(),
        encoding="utf-8",
    )
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path,
        approval_mode=ApprovalMode.NEVER,
        policy_manifest=load_tool_policy_manifest(tmp_path),
    )
    registry = build_command_tool_registry(tmp_path)
    tool = registry.require("run_command")
    args = RunCommandArgs(command="git status --short")
    decision = engine.evaluate(tool.spec, arguments=args, context=context)

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert "allow-git-status" in decision.reason
