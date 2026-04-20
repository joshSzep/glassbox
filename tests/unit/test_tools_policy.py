"""Unit tests for local tool policy evaluation."""

from pathlib import Path

from pydantic import BaseModel

from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRegistry,
    ToolRiskLevel,
    ToolSpec,
)


class ReadFileArgs(BaseModel):
    path: str


class ReadFileResult(BaseModel):
    content: str


class WriteFileArgs(BaseModel):
    path: str
    content: str


class WriteFileResult(BaseModel):
    bytes_written: int


class RunCommandArgs(BaseModel):
    command: str
    cwd: str | None = None


class RunCommandResult(BaseModel):
    summary: str


class ReadFileTool:
    spec = ToolSpec(
        name="read_file",
        description="Read a file from the workspace.",
        input_model=ReadFileArgs,
        output_model=ReadFileResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("path",),
    )

    async def execute(self, arguments: ReadFileArgs) -> ReadFileResult:
        return ReadFileResult(content=arguments.path)


class WriteFileTool:
    spec = ToolSpec(
        name="write_file",
        description="Write a file inside the workspace.",
        input_model=WriteFileArgs,
        output_model=WriteFileResult,
        risk_level=ToolRiskLevel.WORKSPACE_WRITE,
        path_argument_names=("path",),
    )

    async def execute(self, arguments: WriteFileArgs) -> WriteFileResult:
        return WriteFileResult(bytes_written=len(arguments.content))


class RunCommandTool:
    spec = ToolSpec(
        name="run_command",
        description="Run a shell command.",
        input_model=RunCommandArgs,
        output_model=RunCommandResult,
        risk_level=ToolRiskLevel.COMMAND,
        path_argument_names=("cwd",),
        command_argument_name="command",
    )

    async def execute(self, arguments: RunCommandArgs) -> RunCommandResult:
        return RunCommandResult(summary=arguments.command)


def test_policy_allows_read_only_tool_inside_workspace_without_approval() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        ReadFileTool.spec,
        arguments=ReadFileArgs(path="src/glassbox/__init__.py"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.reason == "allowed: read-only tool within workspace scope"


def test_policy_requires_approval_for_workspace_write_in_confirm_mode() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "workspace write inside workspace scope" in decision.reason


def test_policy_blocks_workspace_write_when_approval_mode_is_never() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.NEVER,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "approval mode is never" in decision.reason


def test_policy_blocks_out_of_scope_path_requests() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        ReadFileTool.spec,
        arguments=ReadFileArgs(path="../secrets.txt"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "outside workspace" in decision.reason


def test_policy_blocks_destructive_commands() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="rm -rf build", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert decision.reason == "blocked: destructive command pattern is not allowed"


def test_policy_evaluates_registered_tools_consistently() -> None:
    engine = ToolPolicyEngine()
    registry = ToolRegistry([RunCommandTool()])

    decision = engine.evaluate_registered(
        registry,
        "run_command",
        arguments=RunCommandArgs(command="git status", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "command execution is gated by local policy" in decision.reason
