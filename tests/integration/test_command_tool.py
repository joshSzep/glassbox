"""Integration tests for the command runner tool."""

import asyncio
from pathlib import Path

import pytest

from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import build_command_tool_registry
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
